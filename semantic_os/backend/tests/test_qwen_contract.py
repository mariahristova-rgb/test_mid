"""Offline contracts only: no actual weights, cloud access or inference claims."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import httpx
from semantic_os.backend.assistant.domain import DomainError
from semantic_os.backend.assistant.model_artifacts import ArtifactFile, ModelCache, select_backend
from semantic_os.backend.assistant.qwen import QwenProvider, QwenSettings, VisibleOutput
from semantic_os.backend.agents.llm.provider import ChatMessage, GenerationRequest


class ArtifactTests(unittest.TestCase):
    def fixture(self, reviewed=True):
        files = {'model.gguf': b'GGUFfixture-only', 'LICENSE': b'fixture license'}
        raw = json.dumps({'model_name': 'Qwen3-4B', 'version': 'fixture-v1', 'format': 'gguf',
            'license_spdx': 'Apache-2.0', 'license_reviewed': reviewed,
            'files': [{'path': p, 'sha256': hashlib.sha256(v).hexdigest(), 'size_bytes': len(v), 'generation': 1} for p, v in files.items()]}).encode()
        return files, ModelCache.manifest(raw, hashlib.sha256(raw).hexdigest())

    def test_checksum_and_paths(self):
        with self.assertRaises(DomainError): ModelCache.manifest(b'{}', '0' * 64)
        for path in ('../model.gguf', '/model.gguf', 'C:model.gguf', 'weights.pkl', 'x\\model.gguf'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                ArtifactFile(path=path, sha256='0'*64, size_bytes=4, generation=1)

    def test_verified_cache_reuse_and_tampering(self):
        files, manifest = self.fixture()
        class Source:
            calls = 0
            def download(self, file, target):
                self.calls += 1
                target.write_bytes(files[file.path])
        with tempfile.TemporaryDirectory() as directory:
            cache, source = ModelCache(directory), Source()
            result = cache.sync(manifest, source)
            self.assertTrue(result['downloaded'])
            self.assertFalse(cache.sync(manifest, source)['downloaded'])
            self.assertEqual(source.calls, 2)
            (Path(result['cache']) / 'model.gguf').write_bytes(b'GGUFtampered')
            with self.assertRaises(DomainError): cache.sync(manifest, source)

    def test_license_gate_and_explicit_backend(self):
        _, manifest = self.fixture(False)
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(DomainError):
            ModelCache(directory).sync(manifest, None)
        self.assertEqual(select_backend(manifest), 'llama_cpp')
        self.assertEqual(select_backend(manifest, existing_endpoint='https://owner.example/v1'), 'existing_endpoint')


class QwenTests(unittest.TestCase):
    def provider(self, handler, **kwargs):
        return QwenProvider(QwenSettings(endpoint='https://owner.example/v1'), transport=httpx.MockTransport(handler), **kwargs)

    def request(self, **kwargs):
        return GenerationRequest(messages=[ChatMessage('user', 'Здравейте')], **kwargs)

    def test_nonthinking_and_actual_usage(self):
        receipts = []
        def handler(request):
            body = json.loads(request.content)
            self.assertEqual(body['model'], 'Qwen3-4B')
            self.assertFalse(body['chat_template_kwargs']['enable_thinking'])
            self.assertEqual(body['max_tokens'], 256)
            return httpx.Response(200, json={'choices': [{'message': {'content': '<think>private</think>Здравейте!'}, 'finish_reason': 'stop'}], 'usage': {'prompt_tokens': 12, 'completion_tokens': 4}})
        response = self.provider(handler, usage_sink=receipts.append).generate(self.request())
        self.assertEqual(response.text, 'Здравейте!')
        self.assertEqual(response.prompt_tokens, 12)
        self.assertEqual(len(receipts), 1)

    def test_missing_usage_is_unreported(self):
        response = self.provider(lambda _: httpx.Response(200, json={'choices': [{'message': {'content': 'Hello'}}]})).generate(self.request())
        self.assertFalse(response.metadata['usage_reported'])

    def test_reasoning_fragment_filter(self):
        filter = VisibleOutput()
        self.assertEqual(filter.feed('<thi'), '')
        self.assertEqual(filter.feed('nk>secret</think>Hello'), 'Hello')
        self.assertEqual(filter.feed('', final=True), '')
        with self.assertRaises(DomainError): VisibleOutput().feed('<think>secret', final=True)
        with self.assertRaises(DomainError): VisibleOutput().feed('<thi', final=True)

    def test_cancel_context_and_public_http_denied(self):
        provider = self.provider(lambda _: self.fail('No request should be sent'))
        provider.cancel()
        with self.assertRaises(DomainError): provider.generate(self.request())
        with self.assertRaises(DomainError): self.provider(lambda _: None).payload(GenerationRequest(messages=[ChatMessage('user', 'x'*5000)]))
        with self.assertRaises(DomainError): QwenSettings(endpoint='http://public.example/v1', allow_private_http=True).validate()

    def test_unoffered_tool_denied(self):
        with self.assertRaises(DomainError): QwenProvider.tool_calls([{'function': {'name': 'DeleteTenant', 'arguments': '{}'}}], [])
        with self.assertRaises(DomainError): QwenProvider.tool_calls([{'function': {'name': 'Book', 'arguments': '[]'}}], [{'name': 'Book'}])

    def test_stream_fragments_and_usage(self):
        chunks = [{'choices': [{'delta': {'content': '<thi'}}]}, {'choices': [{'delta': {'content': 'nk>secret</think>Hello'}}]}, {'choices': [], 'usage': {'prompt_tokens': 5, 'completion_tokens': 2}}]
        body = ''.join('data: ' + json.dumps(v) + '\n\n' for v in chunks) + 'data: [DONE]\n\n'
        events = list(self.provider(lambda _: httpx.Response(200, text=body)).stream(self.request()))
        self.assertEqual(''.join(e.get('text', '') for e in events), 'Hello')
        self.assertTrue(events[-1]['metadata']['usage_reported'])


if __name__ == '__main__': unittest.main()
