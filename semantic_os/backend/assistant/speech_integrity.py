"""Verify reviewed speech cache files before loading tensor or YAML artifacts."""
import hashlib
import json
from pathlib import Path


def verify_bgtts_cache(root):
    root = Path(root).resolve()
    manifest = json.loads((root / 'provenance.json').read_text())
    entries = manifest['models']
    wavlm = json.loads((root / 'wavlm-source.json').read_text())
    entries = [*entries, dict(wavlm, path='torch-cache/hub/checkpoints/wavlm_base_plus.pth')]
    required = {'tts/checkpoint_inference.pt', 'tts/samples/sample_female_bg1.wav',
                'codec/config.yaml', 'codec/model.safetensors',
                'torch-cache/hub/checkpoints/wavlm_base_plus.pth'}
    seen = set()
    for entry in entries:
        relative = entry['path'].replace('\\', '/')
        target = (root / relative).resolve()
        if not target.is_relative_to(root) or target == root:
            raise ValueError('Speech artifact path escapes the reviewed cache')
        if relative in seen:
            raise ValueError('Duplicate speech artifact')
        seen.add(relative)
        if target.stat().st_size != entry['size_bytes']:
            raise ValueError('Speech artifact size mismatch')
        digest = hashlib.sha256()
        with target.open('rb') as source:
            for chunk in iter(lambda: source.read(1024 * 1024), b''):
                digest.update(chunk)
        if digest.hexdigest() != entry['sha256']:
            raise ValueError('Speech artifact digest mismatch')
    if not required.issubset(seen):
        raise ValueError('Required speech artifacts missing from manifest')
