"""Stage only Git-visible application/config/docs for a read-only redacted scanner."""
from pathlib import Path
import shutil
import subprocess
ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / 'artifacts/source-scan'
files = subprocess.check_output(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'], cwd=ROOT).decode().split('\0')
count = 0
for name in files:
    if not name:
        continue
    source = ROOT / name
    if not source.is_file() or not source.resolve().is_relative_to(ROOT) or source.is_symlink():
        continue
    if source.name.startswith('.env') and not source.name.endswith('.example'):
        continue
    if source.suffix not in ('.py', '.ps1', '.sh', '.toml', '.ts', '.mts', '.vue', '.mjs', '.json', '.lock', '.css', '.md', '.yml', '.yaml', '.conf', '.txt', '.html', '.example') and not source.name.startswith('Dockerfile') and source.name not in ('.gitignore', '.dockerignore'):
        continue
    target = TARGET / name
    if not target.resolve().is_relative_to(TARGET):
        raise RuntimeError('Unsafe scan target')
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    count += 1
print(f'Staged {count} source/config/documentation files; ignored secrets/data were excluded.')
