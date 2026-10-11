"""Fresh-development SQLite repository with explicit tenant ownership and migrations.

Never opens or migrates a legacy workspace. One process is the supported MVP topology.
"""
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from threading import RLock, local
from uuid import uuid4
from .domain import DomainError, Principal, AssistantConfig
from .language import TEXT

TABLES = ('users', 'assistants', 'agents', 'channel_connections', 'contacts', 'conversations',
          'messages', 'call_sessions', 'agent_executions', 'tool_executions', 'appointments',
          'follow_up_tasks', 'provider_events', 'notification_templates', 'usage_records',
          'approvals', 'audit_events', 'secrets', 'jobs', 'call_events', 'call_participants', 'call_usage', 'voice_tickets', 'voice_transcripts', 'voice_recordings',
          'messaging_events', 'channel_threads', 'email_threads', 'delivery_attempts', 'approved_templates', 'attachments', 'contact_links', 'deletion_requests')

MESSAGING_TABLES = ('messaging_events', 'channel_threads', 'email_threads', 'delivery_attempts', 'approved_templates', 'attachments', 'contact_links', 'deletion_requests')
SAAS_TABLES = ('subscriptions', 'subscription_items', 'billing_customers', 'billing_invoices', 'payment_events',
    'billing_usage', 'usage_reservations', 'usage_warnings', 'onboarding_events', 'verification_tokens',
    'reconciliation_reports', 'privacy_requests', 'support_grants', 'operations_events')
TABLES += SAAS_TABLES


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Store:
    def __init__(self, path: str = ':memory:'):
        if path != ':memory:':
            target = Path(path).resolve()
            if '.ontelyx-workspace' in target.parts:
                raise RuntimeError('Legacy workspace databases cannot be used.')
            target.parent.mkdir(parents=True, exist_ok=True)
        self.lock = RLock()
        self.transaction_state = local()
        self.entitlements = None
        self.operations = None
        self.db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.execute('PRAGMA busy_timeout=5000')
        self.db.execute('PRAGMA journal_mode=WAL')
        self.migrate()

    def migrate(self):
        with self.transaction():
            self.db.execute('CREATE TABLE IF NOT EXISTS schema_migrations(version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)')
            if self.db.execute('SELECT 1 FROM schema_migrations WHERE version=1').fetchone():
                self._migrate_jobs()
                self._migrate_voice()
                self._migrate_messaging()
                self._migrate_saas()
                return
            self.db.execute('CREATE TABLE tenants(id TEXT PRIMARY KEY, data TEXT NOT NULL, created_at TEXT NOT NULL)')
            for table in TABLES:
                if table in SAAS_TABLES or table in MESSAGING_TABLES or table in ('jobs', 'call_events', 'call_participants', 'call_usage', 'voice_tickets', 'voice_transcripts', 'voice_recordings'):
                    continue
                foreign = ''
                if table in ('conversations', 'channel_connections'):
                    foreign += ', FOREIGN KEY(tenant_id,assistant_id) REFERENCES assistants(tenant_id,id)'
                if table in ('messages', 'call_sessions', 'agent_executions', 'tool_executions', 'approvals'):
                    foreign += ', FOREIGN KEY(tenant_id,conversation_id) REFERENCES conversations(tenant_id,id)'
                self.db.execute(f'''CREATE TABLE {table} (
                    tenant_id TEXT NOT NULL REFERENCES tenants(id), id TEXT NOT NULL,
                    assistant_id TEXT, conversation_id TEXT, external_key TEXT,
                    data TEXT NOT NULL, created_at TEXT NOT NULL,
                    PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,external_key){foreign})''')
                self.db.execute(f'CREATE INDEX {table}_history ON {table}(tenant_id,conversation_id,created_at)')
            self.db.execute('INSERT INTO schema_migrations VALUES(1,?)', (now(),))
            self._migrate_jobs()
            self._migrate_voice()
            self._migrate_messaging()
            self._migrate_saas()

    def _migrate_saas(self):
        if self.db.execute('SELECT 1 FROM schema_migrations WHERE version=5').fetchone(): return
        self.db.execute('CREATE TABLE saas_plans(id TEXT PRIMARY KEY,data TEXT NOT NULL,created_at TEXT NOT NULL)')
        self.db.execute('CREATE TABLE platform_audit(id TEXT PRIMARY KEY,data TEXT NOT NULL,created_at TEXT NOT NULL)')
        for table in SAAS_TABLES:
            self.db.execute(f'''CREATE TABLE {table} (
                tenant_id TEXT NOT NULL REFERENCES tenants(id), id TEXT NOT NULL,
                assistant_id TEXT, conversation_id TEXT, external_key TEXT,
                data TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,external_key),
                FOREIGN KEY(tenant_id,conversation_id) REFERENCES conversations(tenant_id,id))''')
            self.db.execute(f'CREATE INDEX {table}_history ON {table}(tenant_id,conversation_id,created_at)')
        self.db.execute("CREATE INDEX billing_usage_period ON billing_usage(tenant_id,json_extract(data,'$.billing_period'),json_extract(data,'$.category'))")
        for action in ('UPDATE', 'DELETE'):
            self.db.execute(f"CREATE TRIGGER billing_usage_no_{action.lower()} BEFORE {action} ON billing_usage BEGIN SELECT RAISE(ABORT,'Append-only billing ledger'); END")
        self.db.execute('INSERT INTO schema_migrations VALUES(5,?)', (now(),))

    def _migrate_messaging(self):
        if self.db.execute('SELECT 1 FROM schema_migrations WHERE version=4').fetchone(): return
        for table in MESSAGING_TABLES:
            self.db.execute(f'''CREATE TABLE {table} (
                tenant_id TEXT NOT NULL REFERENCES tenants(id), id TEXT NOT NULL,
                assistant_id TEXT, conversation_id TEXT, external_key TEXT,
                data TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,external_key),
                FOREIGN KEY(tenant_id,conversation_id) REFERENCES conversations(tenant_id,id))''')
            self.db.execute(f'CREATE INDEX {table}_history ON {table}(tenant_id,conversation_id,created_at)')
        self.db.execute('INSERT INTO schema_migrations VALUES(4,?)', (now(),))

    def _migrate_voice(self):
        if self.db.execute('SELECT 1 FROM schema_migrations WHERE version=3').fetchone():
            return
        for table in ('call_events', 'call_participants', 'call_usage', 'voice_tickets', 'voice_transcripts', 'voice_recordings'):
            self.db.execute(f'''CREATE TABLE {table} (
                tenant_id TEXT NOT NULL REFERENCES tenants(id), id TEXT NOT NULL,
                assistant_id TEXT, conversation_id TEXT, external_key TEXT,
                data TEXT NOT NULL, created_at TEXT NOT NULL,
                PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,external_key),
                FOREIGN KEY(tenant_id,conversation_id) REFERENCES conversations(tenant_id,id))''')
            self.db.execute(f'CREATE INDEX {table}_history ON {table}(tenant_id,conversation_id,created_at)')
        # Add lifecycle metadata to earlier mock sessions without dropping data or
        # overwriting transcripts/business records. Legacy retention remains owner-managed.
        for row in self.db.execute('SELECT tenant_id,id,data,created_at FROM call_sessions').fetchall():
            record = json.loads(row['data'])
            started = record.get('events', [{}])[0].get('at', row['created_at']) if record.get('events') else row['created_at']
            defaults = {'started_at': started, 'ended_at': None, 'duration_seconds': 0,
                        'provider_call_id': record.get('call_id', row['id']), 'connection_id': None,
                        'caller_identifier': 'legacy_unknown', 'owner_user_id': 'system',
                        'last_activity_at': started, 'last_response': '', 'stream_active': False,
                        'locale_explicit': True, 'locale_established': True, 'error_code': None}
            for key, value in defaults.items(): record.setdefault(key, value)
            self.db.execute('UPDATE call_sessions SET data=? WHERE tenant_id=? AND id=?',
                            (json.dumps(record, ensure_ascii=False), row['tenant_id'], row['id']))
        self.db.execute('INSERT INTO schema_migrations VALUES(3,?)', (now(),))

    def _migrate_jobs(self):
        if self.db.execute('SELECT 1 FROM schema_migrations WHERE version=2').fetchone():
            return
        self.db.execute('''CREATE TABLE IF NOT EXISTS jobs (
            tenant_id TEXT NOT NULL REFERENCES tenants(id), id TEXT NOT NULL,
            assistant_id TEXT, conversation_id TEXT, external_key TEXT,
            data TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(tenant_id,id), UNIQUE(tenant_id,external_key),
            FOREIGN KEY(tenant_id,conversation_id) REFERENCES conversations(tenant_id,id))''')
        self.db.execute('CREATE INDEX IF NOT EXISTS jobs_history ON jobs(tenant_id,conversation_id,created_at)')
        self.db.execute('INSERT INTO schema_migrations VALUES(2,?)', (now(),))

    @contextmanager
    def transaction(self):
        with self.lock:
            if self.db.in_transaction:
                yield self
                return
            self.db.execute('BEGIN IMMEDIATE')
            self.transaction_state.callbacks = []
            try:
                yield self
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise
            finally:
                callbacks = self.transaction_state.callbacks
                self.transaction_state.callbacks = []
                for callback in callbacks:
                    callback()  # Actual provider cost survives a rolled-back business action.

    def after_transaction(self, callback):
        """Internal observation hook, executed after the outer commit or rollback."""
        with self.lock:
            if self.db.in_transaction:
                self.transaction_state.callbacks.append(callback)
            else:
                callback()

    @staticmethod
    def _table(table):
        if table not in TABLES:
            raise ValueError('Unknown repository')
        return table

    def tenant(self, tenant_id):
        with self.lock:
            row = self.db.execute('SELECT data FROM tenants WHERE id=?', (tenant_id,)).fetchone()
            if row is None:
                raise DomainError('not_found', 404)
            return json.loads(row['data'])

    def update_tenant(self, tenant_id, data):
        with self.transaction():
            self.tenant(tenant_id)
            plan = self.entitlements.plan(tenant_id) if self.entitlements else None
            if plan and data.get('retention_days', 1) > plan['retention_days']: raise DomainError('upgrade_required', 402)
            self.db.execute('UPDATE tenants SET data=? WHERE id=?', (json.dumps(data, ensure_ascii=False), tenant_id))

    def add(self, table, tenant_id, data, *, id=None, external_key=None):
        table = self._table(table)
        record = {**data, 'id': id or uid(), 'tenant_id': tenant_id}
        with self.transaction():
            if self.entitlements: self.entitlements.before_add(table, tenant_id, record)
            try:
                self.db.execute(f'INSERT INTO {table} VALUES(?,?,?,?,?,?,?)', (
                    tenant_id, record['id'], record.get('assistant_id'), record.get('conversation_id'),
                    external_key, json.dumps(record, ensure_ascii=False), now()))
            except sqlite3.IntegrityError:
                raise DomainError('conflict', 409) from None
            if self.entitlements: self.entitlements.after_add(table, tenant_id, record)
        return record

    def get(self, table, tenant_id, id):
        table = self._table(table)
        with self.lock:
            row = self.db.execute(f'SELECT data FROM {table} WHERE tenant_id=? AND id=?', (tenant_id, id)).fetchone()
            if row is None:
                raise DomainError('not_found', 404)
            return json.loads(row['data'])

    def find(self, table, tenant_id, external_key):
        table = self._table(table)
        with self.lock:
            row = self.db.execute(f'SELECT data FROM {table} WHERE tenant_id=? AND external_key=?', (tenant_id, external_key)).fetchone()
            return json.loads(row['data']) if row else None

    def list(self, table, tenant_id, conversation_id=None):
        table = self._table(table)
        sql, args = f'SELECT data FROM {table} WHERE tenant_id=?', [tenant_id]
        if conversation_id:
            sql += ' AND conversation_id=?'
            args.append(conversation_id)
        # SQLite rowid preserves reception order even when wall-clock timestamps tie.
        sql += ' ORDER BY rowid'
        with self.lock:
            return [json.loads(row['data']) for row in self.db.execute(sql, args)]

    def count(self, table, tenant_id):
        table = self._table(table)
        with self.lock:
            return self.db.execute(f'SELECT COUNT(*) FROM {table} WHERE tenant_id=?', (tenant_id,)).fetchone()[0]

    def inbox(self, tenant_id, *, filters=None, from_date=None, to_date=None, limit=None, cursor=None, identity=None, to_date_exclusive=False):
        """One indexed SQL statement instead of per-conversation Python reads.

        Legacy callers retain ascending reception order. Bounded pages use stable
        descending rowid cursors; filters are applied before pagination.
        """
        where, args = ['c.tenant_id=?'], [tenant_id]
        for key, value in (filters or {}).items():
            if key not in ('channel','assistant_id','status','active_locale'): raise ValueError('Unknown filter')
            if value is not None:
                where.append(f"json_extract(c.data,'$.{key}')=?"); args.append(value)
        if identity:
            where.append('c.id=?'); args.append(identity)
        if cursor is not None:
            where.append('c.rowid<?'); args.append(cursor)
        sql = '''WITH enriched AS (
            SELECT c.rowid AS seq,c.data AS conversation,contact.data AS contact,
                (SELECT m.data FROM messages m WHERE m.tenant_id=c.tenant_id AND m.conversation_id=c.id
                    ORDER BY julianday(json_extract(m.data,'$.timestamp')) DESC,m.rowid DESC LIMIT 1) AS last
            FROM conversations c LEFT JOIN contacts contact ON contact.tenant_id=c.tenant_id
                AND contact.id=json_extract(c.data,'$.contact_id') WHERE ''' + ' AND '.join(where) + ') SELECT * FROM enriched'
        dates = []
        for operator, value in (('>=',from_date),('<' if to_date_exclusive else '<=',to_date)):
            if value is not None:
                dates.append(f"julianday(json_extract(last,'$.timestamp')){operator}julianday(?)"); args.append(value.isoformat())
        if dates: sql += ' WHERE ' + ' AND '.join(dates)
        sql += ' ORDER BY seq ' + ('DESC' if limit is not None else 'ASC')
        if limit is not None:
            sql += ' LIMIT ?'; args.append(limit+1)
        with self.lock: rows = self.db.execute(sql,args).fetchall()
        more = limit is not None and len(rows)>limit
        rows = rows[:limit] if limit is not None else rows
        result=[]
        for row in rows:
            last=json.loads(row['last']) if row['last'] else None
            result.append({**json.loads(row['conversation']), 'contact':json.loads(row['contact']) if row['contact'] else None,
                'last_message':last['content'][:240] if last else '', 'last_message_at':last['timestamp'] if last else None})
        return {'items':result,'next_cursor':rows[-1]['seq'] if more else None} if limit is not None else result

    def update(self, table, tenant_id, id, changes):
        table = self._table(table)
        if table == 'billing_usage': raise DomainError('forbidden', 403)
        if {'tenant_id', 'id', 'assistant_id', 'conversation_id'} & changes.keys():
            raise DomainError('invalid_input', 422)
        with self.transaction():
            previous = self.get(table, tenant_id, id)
            record = {**previous, **changes}
            if self.entitlements: self.entitlements.before_update(table, tenant_id, previous, record)
            self.db.execute(f'UPDATE {table} SET data=? WHERE tenant_id=? AND id=?',
                            (json.dumps(record, ensure_ascii=False), tenant_id, id))
            return record

    def principal(self, subject: str, tenant_id: str) -> Principal:
        record = self.find('users', tenant_id, subject)
        if record is None or not record.get('enabled', True):
            raise DomainError('unauthorized', 401)
        return Principal(tenant_id, record['id'], record['role'], subject)

    def audit(self, principal, action, *, correlation_id='', resource_id='', status='completed'):
        if not correlation_id:
            from .observability import correlation_id as request_correlation
            correlation_id = request_correlation.get()
        return self.add('audit_events', principal.tenant_id, {
            'user_id': principal.user_id, 'action': action, 'resource_id': resource_id,
            'correlation_id': correlation_id, 'status': status, 'timestamp': now()})

    def seed(self, tenant_id='demo', subject='demo-admin', role='admin'):
        """Explicit synthetic fixture provisioning. Idempotent; never overwrites users."""
        with self.transaction():
            data = {'id': tenant_id, 'name': tenant_id, 'default_locale': 'bg-BG',
                    'timezone': 'Europe/Sofia', 'usage_limit': 10000,
                    'retention_days': 30, 'recording_enabled': False, 'transcripts_enabled': False}
            self.db.execute('INSERT OR IGNORE INTO tenants VALUES(?,?,?)', (tenant_id, json.dumps(data), now()))
            if not self.find('users', tenant_id, subject):
                self.add('users', tenant_id, {'subject': subject, 'role': role, 'enabled': True,
                         'preferred_locale': 'en-US'}, external_key=subject)
            if not self.list('assistants', tenant_id):
                self.add('assistants', tenant_id, AssistantConfig(name='Assistant').model_dump(mode='json'), id='default')
            for agent, tools in [('receptionist', ['EscalateToHuman']), ('executor', AssistantConfig(name='a').allowed_tools)]:
                if not self.find('agents', tenant_id, agent):
                    self.add('agents', tenant_id, {'key': agent, 'name': agent, 'supported_locales': ['bg-BG', 'en-US'],
                             'allowed_tools': tools, 'enabled': True, 'instructions': ''}, id=agent, external_key=agent)
            for locale, resources in TEXT.items():
                for key in ('subject', 'reminder', 'appointment_created', 'signature'):
                    identity = locale + ':' + key
                    if not self.find('notification_templates', tenant_id, identity):
                        self.add('notification_templates', tenant_id, {'locale': locale, 'key': key, 'body': resources[key]}, external_key=identity)

    def purge_expired(self, tenant_id, before: str):
        """Explicit tenant retention operation; no startup deletion."""
        with self.transaction():
            # Preserve execution/audit references; clear message bodies and attachments only.
            rows = self.db.execute('SELECT id FROM messages WHERE tenant_id=? AND created_at<?', (tenant_id, before)).fetchall()
            for row in rows:
                self.update('messages', tenant_id, row['id'], {'content': '', 'attachments': [], 'redacted': True})
            return len(rows)

    def close(self):
        self.db.close()


def event_key(channel: str, event_id: str) -> str:
    return sha256((channel + ':' + event_id).encode()).hexdigest()
