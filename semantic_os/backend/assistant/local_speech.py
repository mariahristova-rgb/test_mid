"""Persistent local engines loaded from pinned, reviewed artifacts; never a model name download."""
from hashlib import sha256
import json
from pathlib import Path, PurePosixPath
import re
import struct
from threading import BoundedSemaphore
from time import monotonic
import unicodedata
from .audio import pcm_to_mulaw
from .domain import Capability, DomainError, LOCALES


def reviewed_artifact(root, manifest_path, digest, kind, locale=None):
    root, manifest_path = Path(root), Path(manifest_path)
    if not root.is_absolute() or not root.is_dir() or root.is_symlink(): raise DomainError('unconfigured', 503)
    raw = manifest_path.read_bytes()
    if not re.fullmatch('[a-f0-9]{64}', digest or '') or sha256(raw).hexdigest() != digest:
        raise DomainError('invalid_model_checksum', 422)
    try: data = json.loads(raw)
    except ValueError: raise DomainError('invalid_model_manifest', 422) from None
    if data.get('kind') != kind or data.get('license_reviewed') is not True or not data.get('version') or not data.get('license_spdx'):
        raise DomainError('model_license_required', 409)
    if locale and (data.get('locale') != locale or data.get('listening_approved') is not True):
        raise DomainError('unsupported_locale', 422)
    entries = data.get('files', [])
    if not 2 <= len(entries) <= 100 or len({e['path'] for e in entries}) != len(entries): raise DomainError('invalid_model_manifest', 422)
    if not any(PurePosixPath(e['path']).name.lower() in ('license', 'license.txt', 'license.md') for e in entries):
        raise DomainError('model_license_required', 409)
    for entry in entries:
        path = PurePosixPath(entry['path'])
        if path.is_absolute() or '..' in path.parts or '\\' in entry['path'] or ':' in entry['path']:
            raise DomainError('invalid_model_manifest', 422)
        target = root / entry['path']
        if target.is_symlink() or not target.resolve().is_relative_to(root.resolve()) or not target.is_file():
            raise DomainError('invalid_model_checksum', 422)
        hash = sha256()
        with target.open('rb') as source:
            while chunk := source.read(1024*1024): hash.update(chunk)
        if target.stat().st_size != entry['size_bytes'] or hash.hexdigest() != entry['sha256']:
            raise DomainError('invalid_model_checksum', 422)
    return data


def resample_pcm(data, source_rate, target_rate=8000):
    if not 8000 <= source_rate <= 48000 or target_rate != 8000 or len(data) % 2:
        raise DomainError('unsupported_audio', 422)
    values = [v for v, in struct.iter_unpack('<h', data)]
    if not values: return b''
    # Linear interpolation for narrowband demo output; verify quality with real voice audio.
    count = len(values)*target_rate//source_rate
    out = []
    for index in range(count):
        position = index*source_rate/target_rate
        left = int(position); fraction = position-left
        out.append(round(values[left]*(1-fraction)+values[min(left+1, len(values)-1)]*fraction))
    return struct.pack('<'+'h'*len(out), *out)


class FasterWhisperProvider:
    capability = Capability('faster_whisper', 'LIVE_UNVERIFIED', features=('local_pcm16',), limitations=('real_audio_unverified',))

    def __init__(self, root, manifest, digest, *, device='cpu', compute_type='int8', factory=None, timeout=20, samples_factory=None, vad_filter=False, chunk_seconds=None, cpu_threads=4, vocabulary=None):
        data = reviewed_artifact(root, manifest, digest, 'stt')
        paths = {e['path'] for e in data['files']}
        if not {'model.bin', 'config.json', 'tokenizer.json'} <= paths or set(data.get('locales', [])) != set(LOCALES):
            raise DomainError('invalid_model_manifest', 422)
        if factory is None:
            try: from faster_whisper import WhisperModel as factory
            except ImportError: raise DomainError('unconfigured', 503) from None
        self.model = factory(str(Path(root)), device=device, compute_type=compute_type, local_files_only=True, num_workers=1, cpu_threads=cpu_threads)
        self.slot, self.timeout = BoundedSemaphore(1), timeout
        self.samples_factory = samples_factory
        self.vad_filter = vad_filter
        self.chunk_seconds=chunk_seconds
        self.vocabulary=vocabulary or {}
        if any(locale not in LOCALES or not isinstance(text,str) or len(text)>500 for locale,text in self.vocabulary.items()):
            raise DomainError('invalid_input',422)

    def require(self, locale):
        if locale not in LOCALES: raise DomainError('unsupported_locale', 422)

    def transcribe(self, pcm, locale):
        if locale is not None: self.require(locale)
        if len(pcm) % 2 or not 0 < len(pcm) <= 30*32000: raise DomainError('unsupported_audio', 422)
        if not self.slot.acquire(timeout=self.timeout): raise DomainError('timeout', 504)
        start = monotonic()
        try:
            if self.samples_factory: samples = self.samples_factory(pcm)
            else:
                import numpy as np
                samples = np.frombuffer(pcm, dtype='<i2').astype(np.float32)/32768
            language={'bg-BG':'bg','en-US':'en'}.get(locale)
            options={}
            if locale in self.vocabulary: options['initial_prompt']=self.vocabulary[locale]
            segments, info = self.model.transcribe(samples, language=language,
                beam_size=1, condition_on_previous_text=False, vad_filter=self.vad_filter,chunk_length=self.chunk_seconds,max_new_tokens=96,**options)
            text = []
            for segment in segments:
                if monotonic()-start > self.timeout: raise DomainError('timeout', 504)
                text.append(segment.text)
                if sum(map(len, text)) > 10000: raise DomainError('limit_reached', 413)
            if getattr(info, 'language', None) not in ((None,language) if language else ('bg','en')):
                raise DomainError('unsupported_locale', 422)
            return ' '.join(text).strip()
        finally: self.slot.release()


class PiperProvider:
    capability = Capability('piper', 'LIVE_UNVERIFIED', features=('local_mulaw',), limitations=('real_audio_unverified',))

    def __init__(self, artifacts, *, factory=None, timeout=20):
        if set(artifacts) != set(LOCALES): raise DomainError('unsupported_locale', 422)
        self.voices, self.voice_ids, self.timeout = {}, {}, timeout
        self.slot = BoundedSemaphore(1)
        if factory is None:
            try:
                from piper import PiperVoice
                factory = PiperVoice.load
            except ImportError: raise DomainError('unconfigured', 503) from None
        for locale, artifact in artifacts.items():
            root = Path(artifact['root'])
            data = reviewed_artifact(root, artifact['manifest'], artifact['sha256'], 'tts', locale)
            model, config = data.get('model_file', ''), data.get('config_file', '')
            paths = {e['path'] for e in data['files']}
            if model not in paths or config not in paths or not model.endswith('.onnx') or not config.endswith('.json'):
                raise DomainError('invalid_model_manifest', 422)
            config_data = json.loads((root/config).read_text(encoding='utf-8'))
            language = {'bg-BG':'bg_BG','en-US':'en_US'}[locale]
            if config_data.get('language', {}).get('code') != language or config_data.get('phoneme_type') != 'espeak':
                raise DomainError('unsupported_locale', 422)
            self.voice_ids[locale] = data['voice_id']
            self.voices[locale] = factory(str(root/model), config_path=str(root/config), use_cuda=False)

    def synthesize(self, text, locale, voice=None):
        if locale not in self.voices or voice != self.voice_ids[locale]: raise DomainError('unsupported_locale', 422)
        if not text.strip() or len(text) > 2000: raise DomainError('invalid_input', 422)
        text = unicodedata.normalize('NFC', text).replace('[[', '').replace(']]', '')
        if not self.slot.acquire(timeout=self.timeout): raise DomainError('timeout', 504)
        start, output = monotonic(), bytearray()
        try:
            for chunk in self.voices[locale].synthesize(text):
                if monotonic()-start > self.timeout: raise DomainError('timeout', 504)
                if chunk.sample_width != 2 or chunk.sample_channels != 1: raise DomainError('unsupported_audio', 422)
                output.extend(pcm_to_mulaw(resample_pcm(chunk.audio_int16_bytes, chunk.sample_rate)))
                if len(output) > 60*8000: raise DomainError('limit_reached', 413)
            if not output: raise DomainError('provider_error', 502)
            return bytes(output)
        finally: self.slot.release()
