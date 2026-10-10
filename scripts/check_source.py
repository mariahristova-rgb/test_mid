"""Offline syntax, import-boundary and redacted credential-pattern checks.

Complements environment-secret scanning and CI gitleaks; is not a certification.
"""
import ast
from pathlib import Path
import re
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
SKIP = {'.git', '.venv', 'node_modules', '__pycache__', '.pytest_cache', '.ontelyx-workspace', '.assistant-data', '.assistant-model-cache', 'dist', 'artifacts'}
FORBIDDEN = {'semantic_os_for_ai', 'semantic_kernel', 'assertion_runtime', 'evolution_runtime',
             'semantic_memory', 'semantic_brain', 'semantic_services', 'semantic_migration',
             'reflection_engine', 'belief_manager', 'ontology_mapper', 'repair_coordinator'}
PATTERNS = [re.compile(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----'),
            re.compile(r'\bAKIA[0-9A-Z]{16}\b'), re.compile(r'\bgh[pousr]_[A-Za-z0-9]{30,}\b'),
            re.compile(r'\bsk-(?:proj-)?[A-Za-z0-9_-]{32,}\b')]


def main():
    errors, checked = [], 0
    files = []
    for directory, subdirs, names in os.walk(ROOT, followlinks=False):
        subdirs[:] = [name for name in subdirs if name not in SKIP]
        files.extend(Path(directory) / name for name in names)
    for path in files:
        if not path.is_file() or SKIP.intersection(path.relative_to(ROOT).parts):
            continue
        if path.name.startswith('.env') and not path.name.endswith('.example'):
            continue
        if path.suffix not in ('.py', '.ts', '.vue', '.json', '.mjs', '.yml', '.yaml'):
            continue
        if path.name == 'package-lock.json' or path.name == 'REMOVED_FILES.json':
            continue
        checked += 1
        text = path.read_text(encoding='utf-8')
        if path.suffix == '.py':
            try:
                tree = ast.parse(text, filename=str(path))
            except SyntaxError:
                errors.append((path, 'python_syntax'))
                continue
            for node in ast.walk(tree):
                names = [x.name for x in node.names] if isinstance(node, ast.Import) else [node.module or ''] if isinstance(node, ast.ImportFrom) else []
                if any(set(name.split('.')) & FORBIDDEN for name in names):
                    errors.append((path, 'excluded_runtime_import'))
            if path.name == 'domain.py' and any(name in text for name in ('import openai', 'import boto3', 'import stripe')):
                errors.append((path, 'sdk_in_domain'))
        if any(pattern.search(text) for pattern in PATTERNS):
            errors.append((path, 'credential_pattern'))
    for path, reason in errors:
        print(f'{path.relative_to(ROOT)}: {reason}; matched values redacted')
    print(f'Checked {checked} source/config files; {len(errors)} failures.')
    return bool(errors)


if __name__ == '__main__':
    sys.exit(main())
