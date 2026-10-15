"""Default-off PostgreSQL integration; never use an existing customer database."""
import os
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch
import unittest
from uuid import uuid4
from semantic_os.backend.assistant.postgres_store import PostgresStore, configured_store, postgres_sql
from semantic_os.backend.assistant.domain import DomainError
from semantic_os.backend.tests import test_customer_booking as booking_fixture


class PostgresConfigurationTests(unittest.TestCase):
    def test_strict_tcp_configuration_rejects_unverified_transport_before_connect(self):
        with patch.dict(os.environ,{'ASSISTANT_ENV':'staging','ASSISTANT_STORAGE_BACKEND':'postgresql','ASSISTANT_POSTGRES_DSN':'host=127.0.0.1 dbname=synthetic sslmode=disable'}):
            with self.assertRaises(RuntimeError):configured_store()

    def test_strict_missing_or_sqlite_backend_fails_closed(self):
        for backend in ('','sqlite','unknown'):
            with patch.dict(os.environ,{'ASSISTANT_ENV':'staging','ASSISTANT_STORAGE_BACKEND':backend}):
                with self.assertRaises(RuntimeError): configured_store()

    def test_translation_preserves_literal_question_and_typed_json(self):
        self.assertEqual(postgres_sql("SELECT '?' WHERE id=?"),"SELECT '?' WHERE id=%s")
        self.assertIn('AS numeric',postgres_sql("SELECT sum(json_extract(data,'$.quantity')) FROM billing_usage"))
        self.assertIn('WHEN \'true\' THEN 1',postgres_sql("SELECT json_extract(data,'$.active')"))


@unittest.skipUnless(os.getenv('PHASE26C_PG_DISPOSABLE')=='true','BLOCKED: explicit disposable PostgreSQL runtime required')
class PostgresBookingRuntimeTests(booking_fixture.CustomerBookingTests):
    def setUp(self):
        import psycopg
        self.dsn=os.environ['PHASE26C_PG_DSN']
        info=psycopg.conninfo.conninfo_to_dict(self.dsn)
        if info.get('host')!='127.0.0.1' or info.get('port')!='55426' or info.get('dbname')!='phase26c_fixture':
            raise RuntimeError('Only named loopback disposable fixture is permitted')
        self.schema='fixture_'+uuid4().hex
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            conn.execute('CREATE SCHEMA '+self.schema)
        self.addCleanup(self.drop_fixture)
        with patch('semantic_os.backend.tests.test_customer_booking.Store',lambda:PostgresStore(self.dsn,schema=self.schema,migrate=True,pool_size=2)):
            super().setUp()

    def drop_fixture(self):
        import psycopg
        with psycopg.connect(self.dsn,autocommit=True) as conn:
            conn.execute('DROP SCHEMA '+self.schema+' CASCADE')

    def test_independent_workers_claim_once_and_restart_preserves_uncertainty(self):
        from semantic_os.backend.assistant.api import create_app
        self.app.state.customer_booking.configure(self.actor,self.connection['id'],self.connection['revision'],True)
        self.queue('en-US')
        second=PostgresStore(self.dsn,schema=self.schema,pool_size=2)
        self.addCleanup(second.close)
        service=self.app.state.customer_oauth
        options={'applications':list(service.apps.values()),'http':service.http,'platform_secret':service.platform_secret,'verify_identity':service.verify_identity}
        app2=create_app(store=second,demo_enabled=True,demo_token='synthetic-runtime-token',encryption_key=self.key,clock=lambda:self.now,customer_oauth_options=options)
        self.fail_after_write=True
        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(lambda bridge:bridge.worker(),[self.app.state.customer_booking,app2.state.customer_booking]))
        self.assertEqual(self.posts,1)
        self.assertEqual(second.list('appointments','demo')[0]['status'],'uncertain_external')
        self.now+=timedelta(seconds=61)
        app2.state.customer_booking.worker()
        self.assertEqual(self.posts,1)
        self.assertEqual(self.store.list('appointments','demo')[0]['status'],'confirmed')
        self.assertLessEqual(second.pool.get_stats()['pool_size'],2)

    def test_database_constraints_ledger_and_transaction_rollback(self):
        conversation=self.store.add('conversations','demo',{'assistant_id':'default'})
        with self.assertRaises(DomainError):
            self.store.add('messages','other',{'conversation_id':conversation['id']})
        with self.assertRaises(RuntimeError):
            with self.store.transaction():
                self.store.add('contacts','demo',{'name':'Rolled back'},external_key='rollback')
                raise RuntimeError('synthetic crash')
        self.assertIsNone(self.store.find('contacts','demo','rollback'))
        entry=self.store.add('billing_usage','demo',{'quantity':1,'category':'synthetic','billing_period':'2026-10'})
        with self.assertRaises(sqlite3.IntegrityError):
            self.store.db.execute('DELETE FROM billing_usage WHERE tenant_id=? AND id=?',('demo',entry['id']))
        self.assertEqual(self.store.get('billing_usage','demo',entry['id'])['quantity'],1)

    def test_query_dialects_and_failed_migration_leave_existing_data(self):
        self.queue()
        self.assertTrue(self.store.inbox('demo'))
        row=self.store.db.execute("SELECT strftime('%Y-%m-%d',?),julianday(?)",('2026-10-15T15:00:00+03:00','2026-10-15T15:00:00+03:00')).fetchone()
        self.assertEqual(row[0],'2026-10-15')
        with self.store.pool.connection() as conn:
            with self.assertRaises(Exception):
                with conn.transaction():
                    conn.execute('CREATE TABLE failed_migration_probe(id integer)')
                    conn.execute('SELECT missing_migration_function()')
            self.assertIsNone(conn.execute("SELECT to_regclass('failed_migration_probe')").fetchone()[0])
        self.assertEqual(len(self.store.list('appointments','demo')),1)
