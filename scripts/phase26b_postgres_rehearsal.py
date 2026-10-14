"""Isolated synthetic SQLite -> PostgreSQL -> dump/restore rehearsal.

Does not modify the runtime Store or read any customer database. Requires an
explicitly labelled disposable Docker container with network disabled/no ports.
"""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_os.backend.assistant.store import Store


def docker(*args, input=None):
    return subprocess.run(['docker', *args], input=input, capture_output=True, check=True).stdout


def identifier(value):
    if not value.replace('_', '').isalnum():
        raise ValueError('Unsafe fixture identifier')
    return '"' + value + '"'


def literal(value, json_column=False):
    if value is None:
        return 'NULL'
    if isinstance(value, int):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'" + ('::jsonb' if json_column else '')


def canonical(rows):
    values = []
    for row in rows:
        row = dict(row)
        if isinstance(row.get('data'), str):
            row['data'] = json.loads(row['data'])
        values.append(row)
    return sorted(values, key=lambda r: json.dumps(r, sort_keys=True))


def digest(rows):
    return sha256(json.dumps(canonical(rows), sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def rehearse(container):
    meta = json.loads(docker('inspect', container))[0]
    if (meta['Config']['Labels'].get('purpose') != 'test-mid-phase26b'
            or meta['HostConfig']['NetworkMode'] != 'none' or meta['HostConfig']['PortBindings']):
        raise RuntimeError('Only the isolated labelled fixture container is permitted')

    def sql(statement, db='postgres'):
        return docker('exec', '-i', container, 'psql', '-X', '-qAt', '-v', 'ON_ERROR_STOP=1',
                      '-U', 'postgres', '-d', db, input=statement.encode())

    sql('SELECT 1;')
    with tempfile.TemporaryDirectory(prefix='phase26b-synthetic-') as directory:
        source = Store(str(Path(directory) / 'source.sqlite3'))
        try:
            source.seed('fixture-a', 'synthetic-admin-a')
            source.seed('fixture-b', 'synthetic-admin-b')
            # Unicode, JSON, quotes and timezone strings exercise real serialization.
            for tenant, name in [('fixture-a', 'Синтетичен клиент'), ('fixture-b', "Synthetic O'Brien")]:
                contact=source.add('contacts', tenant, {'name': name, 'locale': 'bg-BG' if tenant == 'fixture-a' else 'en-US'})
                conversation=source.add('conversations',tenant,{'assistant_id':'default','channel':'web_chat','active_locale':'bg-BG' if tenant=='fixture-a' else 'en-US'})
                appointment=source.add('appointments',tenant,{'conversation_id':conversation['id'],'assistant_id':'default','contact_id':contact['id'],'starts_at':'2026-10-15T15:00:00+03:00','duration_minutes':30,'timezone':'Europe/Sofia','status':'confirmed','provider':'customer_google','google_event_id':'synthetic-event'})
                source.add('jobs',tenant,{'kind':'customer_calendar_create','status':'completed','appointment_id':appointment['id'],'conversation_id':conversation['id'],'event_id':'synthetic-event'},external_key='synthetic-job')
                source.add('messages',tenant,{'conversation_id':conversation['id'],'direction':'outbound','content':'Синтетично потвърждение' if tenant=='fixture-a' else 'Synthetic confirmation'})
            backup = sqlite3.connect(str(Path(directory) / 'rollback.sqlite3'))
            source.db.backup(backup)
            backup.close()
            tables = [r[0] for r in source.db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
            snapshots, schema, inserts = {}, [], []
            # Preserve columns, composite PKs, uniqueness and tenant foreign keys.
            for table in tables:
                columns = source.db.execute('PRAGMA table_info(' + identifier(table) + ')').fetchall()
                definitions = [identifier(c['name']) + ' ' + ('JSONB' if c['name'] == 'data' else
                    'BIGINT' if 'INT' in c['type'].upper() else 'TEXT') + (' NOT NULL' if c['notnull'] else '') for c in columns]
                pk = [c['name'] for c in sorted(columns, key=lambda c: c['pk']) if c['pk']]
                if pk:
                    definitions.append('PRIMARY KEY (' + ','.join(map(identifier, pk)) + ')')
                for index in source.db.execute('PRAGMA index_list(' + identifier(table) + ')'):
                    if index['unique'] and index['origin'] != 'pk':
                        cols = [c['name'] for c in source.db.execute('PRAGMA index_info(' + identifier(index['name']) + ')')]
                        definitions.append('UNIQUE (' + ','.join(map(identifier, cols)) + ')')
                schema.append('CREATE TABLE ' + identifier(table) + ' (' + ','.join(definitions) + ');')
                rows = [dict(r) for r in source.db.execute('SELECT * FROM ' + identifier(table))]
                snapshots[table] = rows
                for row in rows:
                    inserts.append('INSERT INTO ' + identifier(table) + ' (' + ','.join(map(identifier, row)) + ') VALUES ('
                                   + ','.join(literal(v, k == 'data') for k, v in row.items()) + ');')
            constraints = []
            for table in tables:
                groups = {}
                for fk in source.db.execute('PRAGMA foreign_key_list(' + identifier(table) + ')'):
                    groups.setdefault(fk['id'], []).append(dict(fk))
                for rows in groups.values():
                    rows.sort(key=lambda r: r['seq'])
                    constraints.append('ALTER TABLE ' + identifier(table) + ' ADD FOREIGN KEY ('
                        + ','.join(identifier(r['from']) for r in rows) + ') REFERENCES '
                        + identifier(rows[0]['table']) + ' (' + ','.join(identifier(r['to']) for r in rows) + ');')
            sql('BEGIN;\n' + '\n'.join(schema + inserts + constraints) + '\nCOMMIT;')
            dump = docker('exec', container, 'pg_dump', '-U', 'postgres', '-Fc', 'postgres')
            sql('CREATE DATABASE phase26b_restore;')
            docker('exec', '-i', container, 'pg_restore', '--exit-on-error', '-U', 'postgres',
                   '-d', 'phase26b_restore', input=dump)
            results = []
            for table in tables:
                expected = digest(snapshots[table])
                query = 'SELECT coalesce(json_agg(row_to_json(r)),\'[]\'::json) FROM ' + identifier(table) + ' r;'
                for db in ('postgres', 'phase26b_restore'):
                    actual = json.loads(sql(query, db))
                    if digest(actual) != expected:
                        raise RuntimeError('Synthetic checksum mismatch: ' + table)
                results.append({'table': table, 'rows': len(snapshots[table]), 'checksum': expected})
            rollback = sqlite3.connect(str(Path(directory) / 'rollback.sqlite3'))
            rollback.row_factory = sqlite3.Row
            try:
                if rollback.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                    raise RuntimeError('Rollback integrity failed')
                for table in tables:
                    if digest(rollback.execute('SELECT * FROM ' + identifier(table)).fetchall()) != digest(snapshots[table]):
                        raise RuntimeError('Rollback checksum mismatch')
            finally:
                rollback.close()
            return {'scope': 'SYNTHETIC_DATA_PORTABILITY_ONLY', 'tables': results,
                    'foreign_keys_translated': len(constraints), 'postgres_import': 'PASS',
                    'postgres_dump_restore': 'PASS', 'sqlite_rollback': 'PASS',
                    'runtime_postgres_ready': False, 'production_ready': False}
        finally:
            source.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--container', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = rehearse(args.container)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k != 'tables'}))
