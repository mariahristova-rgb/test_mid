"""Fresh database and forward migration validation without touching runtime data."""
import argparse
import json
from pathlib import Path
import sys
import tempfile
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.store import Store

def check():
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / 'fixture.sqlite3'
        store = Store(path)
        try:
            store.seed()
            before = store.count('assistants', 'demo')
            store.migrate(); store.migrate()
            result = {'schema_versions': [r[0] for r in store.db.execute('SELECT version FROM schema_migrations ORDER BY version')],
                'foreign_keys_ok': not store.db.execute('PRAGMA foreign_key_check').fetchall(),
                'integrity_ok': store.db.execute('PRAGMA integrity_check').fetchone()[0] == 'ok',
                'data_preserved': before == store.count('assistants', 'demo')}
        finally: store.close()
        restored = Store(path)
        try: assert restored.count('assistants', 'demo') == before
        finally: restored.close()
        assert result['schema_versions'] == [1, 2, 3, 4, 5] and all(result[k] for k in ('foreign_keys_ok', 'integrity_ok', 'data_preserved'))
        return result
if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path); args = parser.parse_args()
    result = json.dumps(check(), indent=2)
    if args.output: args.output.parent.mkdir(parents=True, exist_ok=True); args.output.write_text(result + '\n')
    print(result)
