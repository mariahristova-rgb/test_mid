"""Deployment-only, read-only, pinned artifact synchronization. Never fetches a registry model."""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
from typing import Literal
from pydantic import Field, model_validator
from .domain import Contract, DomainError
from .store import uid


class ArtifactFile(Contract):
    path: str = Field(min_length=1, max_length=300)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    size_bytes: int = Field(ge=1, le=100_000_000_000)
    generation: int = Field(ge=1)

    @model_validator(mode='after')
    def safe_path(self):
        path = PurePosixPath(self.path)
        if path.is_absolute() or '..' in path.parts or '\\' in self.path or ':' in self.path or any(ord(c) < 32 for c in self.path):
            raise ValueError('Invalid artifact path')
        if path.suffix not in ('.json', '.safetensors', '.gguf', '.txt', '.md', '.jinja', '.model') and path.name not in ('LICENSE', 'NOTICE', 'MODEL_CARD', 'README'):
            raise ValueError('Executable/pickle artifact formats are not permitted')
        return self


class QwenManifest(Contract):
    model_name: Literal['Qwen3-4B', 'Qwen3-8B'] = 'Qwen3-4B'
    version: str = Field(pattern=r'^[a-zA-Z0-9_-][a-zA-Z0-9_.-]{0,79}$')
    format: Literal['gguf', 'hf_safetensors']
    license_spdx: str = Field(min_length=1, max_length=80)
    license_reviewed: bool = False
    files: list[ArtifactFile] = Field(min_length=2, max_length=500)

    @model_validator(mode='after')
    def required_files(self):
        paths = [f.path for f in self.files]
        if len(set(paths)) != len(paths) or not any(PurePosixPath(p).name.lower() in ('license', 'license.txt', 'license.md') for p in paths):
            raise ValueError('Unique files and a license file are required')
        if self.format == 'gguf' and not any(p.endswith('.gguf') for p in paths): raise ValueError('Missing GGUF')
        if self.format == 'hf_safetensors' and (not any(p.endswith('.safetensors') for p in paths) or not {'config.json', 'tokenizer.json', 'tokenizer_config.json'} <= set(paths)):
            raise ValueError('Missing model/tokenizer configuration')
        return self


class ReadOnlyGCS:
    def __init__(self, bucket, prefix, client=None):
        if not bucket or not prefix or prefix.startswith('/') or '..' in PurePosixPath(prefix).parts:
            raise DomainError('unconfigured', 503)
        if client is None:
            try:
                from google.cloud import storage
                client = storage.Client()  # ADC/workload identity; no credential values accepted from clients.
            except ImportError: raise DomainError('unconfigured', 503) from None
        self.bucket, self.prefix = client.bucket(bucket), prefix.strip('/')

    def download(self, file, target):
        blob = self.bucket.blob(self.prefix + '/' + file.path, generation=file.generation)
        blob.download_to_filename(str(target), if_generation_match=file.generation, checksum='auto')


class ModelCache:
    def __init__(self, directory): self.directory = Path(directory).resolve()

    @staticmethod
    def manifest(raw, expected_digest):
        if not re.fullmatch(r'[a-f0-9]{64}', expected_digest or '') or sha256(raw).hexdigest() != expected_digest:
            raise DomainError('invalid_model_checksum', 422)
        try: return QwenManifest.model_validate_json(raw)
        except ValueError: raise DomainError('invalid_model_manifest', 422) from None

    def target(self, manifest):
        result = (self.directory / manifest.model_name / manifest.version).resolve()
        if not result.is_relative_to(self.directory): raise DomainError('forbidden', 403)
        return result

    @staticmethod
    def verify(root, manifest):
        for file in manifest.files:
            path = root / file.path
            if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or path.stat().st_size != file.size_bytes:
                raise DomainError('invalid_model_checksum', 422)
            digest = sha256()
            with path.open('rb') as source:
                while chunk := source.read(1024 * 1024): digest.update(chunk)
            if digest.hexdigest() != file.sha256: raise DomainError('invalid_model_checksum', 422)
        if manifest.format == 'gguf':
            for file in manifest.files:
                if file.path.endswith('.gguf'):
                    with (root / file.path).open('rb') as source:
                        if source.read(4) != b'GGUF': raise DomainError('invalid_model_format', 422)
        else:
            config = json.loads((root / 'config.json').read_text(encoding='utf-8'))
            if config.get('model_type') != 'qwen3': raise DomainError('invalid_model_format', 422)

    def sync(self, manifest, source):
        if not manifest.license_reviewed: raise DomainError('model_license_required', 409)
        target = self.target(manifest)
        if target.exists():
            self.verify(target, manifest)
            marker = json.loads((target / '.verified.json').read_text(encoding='utf-8'))
            if marker['manifest'] != manifest.model_dump(mode='json'): raise DomainError('conflict', 409)
            return {'cache': str(target), 'downloaded': False, 'format': manifest.format}
        staging = (self.directory / ('partial-' + uid())).resolve()
        if not staging.is_relative_to(self.directory): raise DomainError('forbidden', 403)
        staging.mkdir(parents=True)
        for file in manifest.files:
            destination = (staging / file.path).resolve()
            if not destination.is_relative_to(staging): raise DomainError('forbidden', 403)
            destination.parent.mkdir(parents=True, exist_ok=True)
            source.download(file, destination)
        self.verify(staging, manifest)
        (staging / '.verified.json').write_text(json.dumps({'manifest': manifest.model_dump(mode='json')}), encoding='utf-8')
        target.parent.mkdir(parents=True, exist_ok=True)
        # Both resolved directory paths are verified within the explicitly configured cache.
        if not staging.resolve().is_relative_to(self.directory) or not target.resolve().is_relative_to(self.directory):
            raise DomainError('forbidden', 403)
        staging.rename(target)
        return {'cache': str(target), 'downloaded': True, 'format': manifest.format,
            'artifact_bytes': sum(f.size_bytes for f in manifest.files)}


def select_backend(manifest, *, existing_endpoint='', cuda_verified=False):
    if existing_endpoint: return 'existing_endpoint'
    if manifest.format == 'gguf': return 'llama_cpp'
    if manifest.format == 'hf_safetensors' and cuda_verified: return 'vllm'
    raise DomainError('inference_hardware_required', 409)
