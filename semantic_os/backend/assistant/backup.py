"""Encrypted consistent SQLite snapshots; restores always target a new database."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
from cryptography.fernet import Fernet, InvalidToken
from .domain import DomainError
from .store import uid, Store


class BackupManager:
    def __init__(self, store, directory, key='', *, retention_days=7, rpo_seconds=86400, rto_seconds=3600):
        self.store, self.directory = store, Path(directory).resolve()
        self.cipher = Fernet(key.encode()) if key else None
        self.retention_days, self.rpo_seconds, self.rto_seconds = retention_days, rpo_seconds, rto_seconds

    def create(self):
        if getattr(self.store, 'backend', 'sqlite') != 'sqlite': raise DomainError('unconfigured', 503)
        if not self.cipher: raise DomainError('unconfigured', 503)
        self.directory.mkdir(parents=True, exist_ok=True)
        snapshot = sqlite3.connect(':memory:')
        try:
            with self.store.lock:
                if self.store.db.in_transaction: raise DomainError('conflict', 409)
                self.store.db.backup(snapshot)
            if snapshot.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or snapshot.execute('PRAGMA foreign_key_check').fetchall(): raise DomainError('provider_error', 500)
            data = snapshot.serialize()
            id = uid()
            manifest = {'id': id, 'created_at': datetime.now(timezone.utc).isoformat(), 'schema_version': snapshot.execute('SELECT max(version) FROM schema_migrations').fetchone()[0],
                'sha256': hashlib.sha256(data).hexdigest(), 'payload': self.cipher.encrypt(data).decode()}
            manifest['manifest_token'] = self.cipher.encrypt(json.dumps({k: v for k, v in manifest.items() if k != 'payload'}, sort_keys=True).encode()).decode()
            target = self.directory / ('assistant-backup-' + id + '.json')
            with target.open('x', encoding='utf-8') as output: json.dump(manifest, output)
            return {k: v for k, v in manifest.items() if k not in ('payload', 'manifest_token')} | {'filename': target.name, 'encrypted': True,
                'rpo_target_seconds': self.rpo_seconds, 'rto_target_seconds': self.rto_seconds}
        finally: snapshot.close()

    def restore(self, filename, target):
        if not self.cipher: raise DomainError('unconfigured', 503)
        source = (self.directory / filename).resolve()
        if not source.is_relative_to(self.directory) or source.is_symlink(): raise DomainError('forbidden', 403)
        destination = Path(target).resolve()
        if destination.exists() or Path(str(destination) + '-wal').exists() or Path(str(destination) + '-shm').exists(): raise DomainError('conflict', 409)
        manifest = json.loads(source.read_text(encoding='utf-8'))
        self.validate_manifest(manifest)
        try: data = self.cipher.decrypt(manifest['payload'].encode())
        except (InvalidToken, KeyError): raise DomainError('invalid_input', 422) from None
        if hashlib.sha256(data).hexdigest() != manifest['sha256']: raise DomainError('invalid_input', 422)
        probe = sqlite3.connect(':memory:')
        try:
            if len(data) < 100 or not data.startswith(b'SQLite format 3\x00'): raise DomainError('invalid_input', 422)
            # SQLite documents that deserialize cannot open WAL headers. Change only
            # the validation copy to rollback format; restore the authenticated original.
            validation_copy = bytearray(data)
            validation_copy[18:20] = b'\x01\x01'
            probe.deserialize(bytes(validation_copy))
            if probe.execute('SELECT max(version) FROM schema_migrations').fetchone()[0] > 5: raise DomainError('invalid_input', 422)
            if probe.execute('PRAGMA integrity_check').fetchone()[0] != 'ok' or probe.execute('PRAGMA foreign_key_check').fetchall(): raise DomainError('invalid_input', 422)
            destination.parent.mkdir(parents=True, exist_ok=True)
            with destination.open('xb') as output: output.write(data)
        finally: probe.close()
        restored = Store(str(destination))
        try:
            return {'status': 'restored', 'schema_version': restored.db.execute('SELECT max(version) FROM schema_migrations').fetchone()[0],
                'backup_id': manifest['id'], 'integrity': 'ok', 'foreign_keys': 'ok'}
        finally: restored.close()

    def validate_manifest(self, manifest):
        try:
            trusted = json.loads(self.cipher.decrypt(manifest['manifest_token'].encode()))
        except (InvalidToken, ValueError, KeyError): raise DomainError('invalid_input', 422) from None
        if trusted != {k: v for k, v in manifest.items() if k not in ('payload', 'manifest_token')}: raise DomainError('invalid_input', 422)

    def prune(self):
        """Explicit retention action; authenticates only this manager's named snapshots."""
        if not self.cipher: raise DomainError('unconfigured', 503)
        deleted = 0
        before = datetime.now(timezone.utc) - timedelta(days=self.retention_days)
        for file in self.directory.glob('assistant-backup-*.json'):
            if file.is_symlink() or not file.resolve().is_relative_to(self.directory): continue
            manifest = json.loads(file.read_text(encoding='utf-8'))
            try: self.validate_manifest(manifest)
            except DomainError: continue
            try: self.cipher.decrypt(manifest['payload'].encode())
            except (InvalidToken, KeyError): continue
            if datetime.fromisoformat(manifest['created_at']) < before:
                file.unlink(); deleted += 1
        return {'deleted': deleted}
