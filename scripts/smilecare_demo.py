"""Explicit dedicated demo seed/reset. Never operates on arbitrary tenant IDs."""
import argparse
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.demo_seed import seed_smilecare, reset_smilecare, TENANT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('seed','reset'))
    parser.add_argument('--database', type=Path, required=True)
    parser.add_argument('--mode', choices=('qwen','mock'), default='qwen')
    parser.add_argument('--operator-subject', default='demo-admin', help='Existing verified identity subject for container dashboard access; local fixture default is demo-admin')
    parser.add_argument('--confirm', action='store_true', help='Explicitly authorize demo-only archival reset after stopping its backend')
    args = parser.parse_args()
    if os.getenv('ASSISTANT_ENV') == 'production': parser.error('Demo maintenance is disabled in production')
    if args.action == 'reset' and not args.confirm: parser.error('Reset requires explicit --confirm; stop the dedicated demo backend first')
    workspace = Path(__file__).resolve().parents[1]
    database = args.database.resolve()
    if not database.is_relative_to(workspace / '.assistant-data'): parser.error('Use a dedicated database under test_mid/.assistant-data')
    if args.action == 'reset' and not database.is_file(): parser.error('Demo database does not exist')
    store = Store(str(database))
    try:
        result = seed_smilecare(store, mode=args.mode, operator_subject=args.operator_subject) if args.action == 'seed' else reset_smilecare(store, store.principal('smilecare-demo-admin', TENANT))
        print(result)
    finally: store.close()


if __name__ == '__main__': main()
