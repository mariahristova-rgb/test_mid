"""Offline owner-only tenant/membership provisioning; never an unauthenticated endpoint."""
import argparse
import os
from .store import Store


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--subject', required=True, help='Verified identity subject; never an email match')
    parser.add_argument('--role', choices=('admin', 'operator', 'viewer'), default='admin')
    parser.add_argument('--database', default=os.getenv('ASSISTANT_DATABASE', '.assistant-data/assistant.sqlite3'))
    args = parser.parse_args()
    store = Store(args.database)
    store.seed(args.tenant, args.subject, args.role)
    store.close()
    print('Tenant membership provisioned. No external calls were made.')


if __name__ == '__main__':
    main()
