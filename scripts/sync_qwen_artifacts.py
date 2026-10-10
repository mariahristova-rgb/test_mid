"""Explicit deployment-time sync only; no default bucket, registry or model download."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.model_artifacts import ModelCache, ReadOnlyGCS


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--bucket', required=True)
    parser.add_argument('--prefix', required=True)
    parser.add_argument('--cache', required=True, type=Path)
    args = parser.parse_args()
    cache = ModelCache(args.cache)
    manifest = cache.manifest(args.manifest.read_bytes(), args.manifest_sha256)
    # Review gate before even constructing an authenticated cloud client.
    if not manifest.license_reviewed:
        parser.error('Artifact license/provenance review is required before synchronization')
    result = cache.sync(manifest, ReadOnlyGCS(args.bucket, args.prefix))
    print('Verified cache:', result['cache'], 'downloaded:', result['downloaded'])


if __name__ == '__main__': main()
