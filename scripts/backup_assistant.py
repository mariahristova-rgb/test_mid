"""Operator CLI: readonly live snapshot; restore refuses every existing target."""
import argparse
import json
import os
from pathlib import Path
import sqlite3
import sys
from threading import RLock
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.backup import BackupManager

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['backup', 'restore', 'prune'])
    parser.add_argument('--database', type=Path)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--filename')
    parser.add_argument('--target', type=Path)
    args = parser.parse_args()
    key = os.environ.get('ASSISTANT_BACKUP_ENCRYPTION_KEY', '')
    connection = None
    if args.action == 'backup':
        if not args.database or not args.database.is_file(): parser.error('An existing database is required.')
        connection = sqlite3.connect(args.database.resolve().as_uri() + '?mode=ro', uri=True)
    manager = BackupManager(SimpleNamespace(db=connection, lock=RLock()), args.directory, key,
        retention_days=int(os.getenv('ASSISTANT_BACKUP_RETENTION_DAYS', '7')))
    try:
        if args.action == 'backup': result = manager.create()
        elif args.action == 'prune': result = manager.prune()
        else:
            if not args.filename or not args.target: parser.error('Restore requires a filename and a fresh target.')
            result = manager.restore(args.filename, args.target)
        print(json.dumps(result))
    finally:
        if connection: connection.close()
