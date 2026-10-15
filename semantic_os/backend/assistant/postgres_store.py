"""Bounded PostgreSQL persistence for the existing Store business operations.

Serialized database transactions deliberately preserve SQLite BEGIN IMMEDIATE
semantics across processes. This conservative topology is not a throughput/HA claim.
Only repository-authored SQL is translated; no SQL is accepted from customers.
"""
from contextlib import contextmanager
import json
import re
import sqlite3
from threading import RLock, local
from time import perf_counter
from .store import Store, TABLES, now


class Rows:
    def __init__(self, cursor):
        self.names = [c.name for c in cursor.description] if cursor.description else []
        self.values = cursor.fetchall() if cursor.description else []
        self.rowcount = cursor.rowcount
    def fetchall(self):
        return [Row(self.names, row) for row in self.values]
    def fetchone(self):
        return Row(self.names, self.values[0]) if self.values else None
    def __iter__(self):
        return iter(self.fetchall())


class Row(dict):
    def __init__(self, names, values):
        super().__init__(zip(names, values))
    def __getitem__(self, key):
        return list(self.values())[key] if isinstance(key, int) else super().__getitem__(key)


def postgres_sql(statement):
    """Small audited dialect boundary, retaining JSON text/API serialization."""
    statement = re.sub(r"json_extract\((\w+(?:\.\w+)?),'\$\.([a-z_]+)'\)",
        lambda m: (f"CAST(({m[1]}::jsonb ->> '{m[2]}') AS numeric)" if m[2] == 'quantity'
                   else f"CASE ({m[1]}::jsonb ->> '{m[2]}') WHEN 'true' THEN 1 WHEN 'false' THEN 0 ELSE NULL END" if m[2] in ('active','redacted')
                   else f"({m[1]}::jsonb ->> '{m[2]}')"), statement)
    # Preserve seven-column legacy insert contract with an additional durable cursor.
    statement = re.sub(r'INSERT INTO ('+'|'.join(TABLES)+r') VALUES',
        r'INSERT INTO \1 (tenant_id,id,assistant_id,conversation_id,external_key,data,created_at) VALUES', statement)
    if statement.startswith('INSERT OR IGNORE INTO tenants VALUES'):
        statement = statement.replace('INSERT OR IGNORE', 'INSERT') + ' ON CONFLICT DO NOTHING'
    # SQL placeholders must not replace question marks inside string literals.
    parts = re.split(r"('(?:''|[^'])*')", statement)
    return ''.join(part.replace('?', '%s') if index % 2 == 0 else part.replace('%','%%')
                   for index, part in enumerate(parts))


class Database:
    def __init__(self, store): self.store = store
    @property
    def in_transaction(self): return getattr(self.store.transaction_state, 'connection', None) is not None
    def execute(self, statement, params=()):
        translated = postgres_sql(statement)
        connection = getattr(self.store.transaction_state, 'connection', None)
        write = statement.lstrip().split()[0].upper() not in ('SELECT','WITH')
        if connection is None:
            if write:
                with self.store.transaction(): return self.execute(statement, params)
            with self.store.pool.connection() as connection:
                return self._execute(connection, translated, params)
        return self._execute(connection, translated, params)
    def _execute(self, connection, statement, params):
        import psycopg
        started = perf_counter()
        try:
            # Savepoint permits legacy conflict-to-DomainError handling without
            # leaving the surrounding business transaction aborted.
            with connection.transaction():
                return Rows(connection.execute(statement, params))
        except psycopg.IntegrityError:
            raise sqlite3.IntegrityError('Persistence constraint rejected') from None
        finally:
            self.store.query_count += 1
            self.store.query_seconds += perf_counter()-started


class PostgresStore(Store):
    backend = 'postgresql'
    def __init__(self, dsn, *, pool_size=4, migrate=False, schema='public'):
        from psycopg_pool import ConnectionPool
        if not dsn or not 1 <= pool_size <= 8 or not re.fullmatch(r'[a-z][a-z0-9_]{0,62}',schema):
            raise RuntimeError('Explicit PostgreSQL DSN and bounded pool required')
        self.lock, self.transaction_state = RLock(), local()
        self.entitlements = self.operations = None
        self.query_count, self.query_seconds = 0, 0.0
        self.pool = ConnectionPool(dsn, min_size=1, max_size=pool_size, max_waiting=16,
            timeout=5, open=False, kwargs={'autocommit': True, 'connect_timeout': 5,
                'options': '-c statement_timeout=10000 -c lock_timeout=5000 -c timezone=UTC -c search_path='+schema,
                'application_name': 'ontelyx-assistant'})
        self.db = Database(self)
        try:
            self.pool.open(wait=True, timeout=10)
            if migrate: self.migrate()
            else:
                with self.pool.connection() as conn:
                    if conn.execute('SELECT version FROM store_runtime_migrations').fetchall() != [(1,)]:
                        raise RuntimeError('Reviewed PostgreSQL migration required')
        except BaseException:
            self.pool.close()
            raise

    @contextmanager
    def transaction(self):
        with self.lock:
            if self.db.in_transaction:
                yield self
                return
            callbacks = []
            try:
                with self.pool.connection() as connection:
                    with connection.transaction():
                        # Database-enforced cross-instance writer exclusion. The
                        # lock is released on commit, rollback, or connection loss.
                        connection.execute('SELECT pg_advisory_xact_lock(26260001)')
                        self.transaction_state.connection = connection
                        self.transaction_state.callbacks = callbacks
                        try: yield self
                        finally: self.transaction_state.connection = None
            finally:
                self.transaction_state.callbacks = []
                for callback in callbacks: callback()

    def migrate(self):
        """Bootstrap only empty/new schema; derive tenant FKs from existing migrations."""
        source = Store()
        try:
            with self.pool.connection() as conn, conn.transaction():
                conn.execute('SELECT pg_advisory_xact_lock(26260001)')
                exists = conn.execute("SELECT to_regclass('store_runtime_migrations')").fetchone()[0]
                if exists:
                    if conn.execute('SELECT version FROM store_runtime_migrations').fetchall() != [(1,)]:
                        raise RuntimeError('Unknown PostgreSQL schema version')
                    return
                if conn.execute("SELECT to_regclass('tenants')").fetchone()[0]:
                    raise RuntimeError('Nonempty legacy target requires reviewed offline import')
                tables = [r[0] for r in source.db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
                constraints = []
                for table in tables:
                    columns = source.db.execute(f'PRAGMA table_info({table})').fetchall()
                    defs = [f'"{c["name"]}" '+('INTEGER' if 'INT' in c['type'] else 'TEXT')+(' NOT NULL' if c['notnull'] else '') for c in columns]
                    pk = [c['name'] for c in sorted(columns, key=lambda c: c['pk']) if c['pk']]
                    if pk: defs.append('PRIMARY KEY ('+','.join(pk)+')')
                    for index in source.db.execute(f'PRAGMA index_list({table})'):
                        if index['unique'] and index['origin'] != 'pk':
                            cols = [c['name'] for c in source.db.execute(f'PRAGMA index_info("{index["name"]}")')]
                            defs.append('UNIQUE ('+','.join(cols)+')')
                    if table in TABLES: defs.append('rowid BIGINT GENERATED ALWAYS AS IDENTITY UNIQUE')
                    if any(c['name']=='data' for c in columns): defs.append("CHECK (jsonb_typeof(data::jsonb)='object')")
                    conn.execute(f'CREATE TABLE "{table}" ('+','.join(defs)+')')
                    groups = {}
                    for fk in source.db.execute(f'PRAGMA foreign_key_list({table})'): groups.setdefault(fk['id'], []).append(dict(fk))
                    for rows in groups.values():
                        rows.sort(key=lambda r:r['seq'])
                        constraints.append(f'ALTER TABLE "{table}" ADD FOREIGN KEY ('+','.join(r['from'] for r in rows)+') REFERENCES '+rows[0]['table']+' ('+','.join(r['to'] for r in rows)+')')
                    if table in TABLES: conn.execute(f'CREATE INDEX {table}_history ON {table}(tenant_id,conversation_id,created_at)')
                for statement in constraints: conn.execute(statement)
                conn.execute("CREATE INDEX billing_usage_period ON billing_usage(tenant_id, (data::jsonb->>'billing_period'), (data::jsonb->>'category'))")
                conn.execute("CREATE FUNCTION reject_ledger_change() RETURNS trigger LANGUAGE plpgsql AS $$ BEGIN RAISE EXCEPTION 'Append-only billing ledger' USING ERRCODE='23000'; END $$")
                conn.execute('CREATE TRIGGER billing_usage_append_only BEFORE UPDATE OR DELETE ON billing_usage FOR EACH ROW EXECUTE FUNCTION reject_ledger_change()')
                conn.execute("CREATE FUNCTION julianday(text) RETURNS double precision LANGUAGE sql STABLE AS $$ SELECT EXTRACT(EPOCH FROM $1::timestamptz)::double precision / 86400 + 2440587.5 $$")
                conn.execute("CREATE FUNCTION strftime(text,text) RETURNS text LANGUAGE sql STABLE AS $$ SELECT CASE WHEN $1='%Y-%m-%d' THEN to_char($2::timestamptz,'YYYY-MM-DD') ELSE NULL END $$")
                for row in source.db.execute('SELECT version,applied_at FROM schema_migrations'):
                    conn.execute('INSERT INTO schema_migrations VALUES (%s,%s)', tuple(row))
                conn.execute('CREATE TABLE store_runtime_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
                conn.execute('INSERT INTO store_runtime_migrations VALUES (1,%s)', (now(),))
        finally: source.close()

    def close(self): self.pool.close()


def configured_store():
    """Explicit strict-environment backend; never silently falls back to SQLite."""
    import os
    from .self_hosted import deployment_secret
    backend = os.getenv('ASSISTANT_STORAGE_BACKEND', '')
    strict = os.getenv('ASSISTANT_ENV') in ('production','staging')
    if backend == 'postgresql':
        dsn=deployment_secret('ASSISTANT_POSTGRES_DSN')
        if strict:
            from psycopg.conninfo import conninfo_to_dict
            info=conninfo_to_dict(dsn)
            if not dsn or (info.get('sslmode')!='verify-full' and not info.get('host','').startswith('/cloudsql/')):
                raise RuntimeError('Verified PostgreSQL TLS or reviewed Cloud SQL proxy socket required')
        return PostgresStore(dsn, pool_size=int(os.getenv('ASSISTANT_POSTGRES_POOL_SIZE','4')))
    if backend not in ('','sqlite') or strict:
        raise RuntimeError('Explicit migrated PostgreSQL configuration required')
    return Store(os.getenv('ASSISTANT_DATABASE','.assistant-data/assistant.sqlite3'))
