"""Synthetic local-engine/RTP/ARI contracts. No real speech or SIP acceptance is claimed."""
import asyncio
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
import httpx
from semantic_os.backend.assistant.domain import DomainError
from semantic_os.backend.assistant.local_speech import FasterWhisperProvider, PiperProvider, reviewed_artifact, resample_pcm
from semantic_os.backend.assistant.rtp import RTPDecoder, RTPAudioTransport
from semantic_os.backend.assistant.asterisk import ARISettings, ARIBridge
from semantic_os.backend.assistant.demo_seed import seed_smilecare, reset_smilecare, TENANT
from semantic_os.backend.assistant.calendar import MockCalendarProvider
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.observability import Operations


class SpeechTests(unittest.TestCase):
    def artifact(self, directory, locale=None, approved=True):
        root = Path(directory)/('voice-'+locale if locale else 'stt')
        root.mkdir()
        files = {'LICENSE':b'Synthetic license', 'model.bin':b'fixture', 'tokenizer.json':b'{}', 'config.json':b'{}'} if not locale else {
            'LICENSE':b'Synthetic license', 'voice.onnx':b'fixture-not-onnx', 'voice.json':json.dumps({'language':{'code':{'bg-BG':'bg_BG','en-US':'en_US'}[locale]},'phoneme_type':'espeak'}).encode()}
        for name, value in files.items(): (root/name).write_bytes(value)
        data = {'kind':'tts' if locale else 'stt', 'version':'synthetic-v1', 'license_spdx':'fixture', 'license_reviewed':approved,
            'locales':['bg-BG','en-US'], 'locale':locale, 'listening_approved':approved, 'voice_id':'fixture-'+str(locale),
            'model_file':'voice.onnx', 'config_file':'voice.json',
            'files':[{'path':name, 'size_bytes':len(value), 'sha256':hashlib.sha256(value).hexdigest()} for name,value in files.items()]}
        raw = json.dumps(data).encode(); manifest = Path(directory)/(root.name+'-manifest.json'); manifest.write_bytes(raw)
        return {'root':str(root), 'manifest':str(manifest), 'sha256':hashlib.sha256(raw).hexdigest()}

    def test_stt_local_only_explicit_language_and_input_bounds(self):
        calls = []
        class Engine:
            def transcribe(self, samples, **kwargs):
                calls.append(kwargs)
                return iter([SimpleNamespace(text='Мария Иванова')]), SimpleNamespace(language=kwargs['language'])
        def factory(path, **kwargs):
            self.assertTrue(Path(path).is_absolute())
            self.assertTrue(kwargs['local_files_only'])
            return Engine()
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.artifact(directory)
            provider = FasterWhisperProvider(artifact['root'], artifact['manifest'], artifact['sha256'], factory=factory, samples_factory=lambda p:[0]*len(p))
            self.assertEqual(provider.transcribe(b'\x00\x00'*1600, 'bg-BG'), 'Мария Иванова')
            self.assertEqual(calls[0]['language'], 'bg')
            with self.assertRaises(DomainError): provider.transcribe(b'x', 'bg-BG')
            with self.assertRaises(DomainError): provider.transcribe(b'\x00\x00', 'de-DE')

    def test_tts_locale_selection_sample_rate_and_no_fallback(self):
        called = []
        class Engine:
            def synthesize(self, text):
                called.append(text)
                yield SimpleNamespace(sample_rate=22050, sample_width=2, sample_channels=1, audio_int16_bytes=struct.pack('<h', 1000)*22050)
        with tempfile.TemporaryDirectory() as directory:
            artifacts = {locale:self.artifact(directory, locale) for locale in ('bg-BG','en-US')}
            provider = PiperProvider(artifacts, factory=lambda *a,**k:Engine())
            output = provider.synthesize('Здравейте!', 'bg-BG', 'fixture-bg-BG')
            self.assertEqual(len(output), 8000)
            self.assertEqual(called, ['Здравейте!'])
            with self.assertRaises(DomainError): provider.synthesize('Здравейте!', 'bg-BG', 'fixture-en-US')
            with self.assertRaises(DomainError): PiperProvider({'en-US':artifacts['en-US']}, factory=lambda *a:Engine())

    def test_speech_license_and_checksum_gate_before_loading(self):
        with tempfile.TemporaryDirectory() as directory:
            artifact = self.artifact(directory, approved=False)
            with self.assertRaises(DomainError): FasterWhisperProvider(artifact['root'], artifact['manifest'], artifact['sha256'], factory=lambda *a,**k:self.fail())
        with self.assertRaises(DomainError): resample_pcm(b'x', 22050)


def packet(sequence=1, ssrc=7, payload=None):
    return struct.pack('!BBHII',128,0,sequence,160,ssrc)+(payload if payload is not None else b'\xff'*160)


class RTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_sequence_wrap_reordering_ssrc_and_codec(self):
        decoder = RTPDecoder()
        self.assertEqual(decoder.decode(packet(65535))[0], 1)
        self.assertEqual(decoder.decode(packet(0))[0], 2)
        self.assertIsNone(decoder.decode(packet(0)))
        self.assertIsNone(decoder.decode(packet(65534)))
        with self.assertRaises(DomainError): decoder.decode(packet(1, ssrc=8))
        with self.assertRaises(DomainError): RTPDecoder().decode(packet(payload=b'x'))
        with self.assertRaises(DomainError): RTPDecoder().decode(bytes([128,8])+packet()[2:])

    async def test_negotiated_peer_and_backpressure(self):
        transport = RTPAudioTransport()
        transport.peer = ('127.0.0.1',10000)
        transport.datagram_received(packet(), ('127.0.0.1',10001))
        self.assertTrue(transport.queue.empty())
        for seq in range(1,130): transport.datagram_received(packet(seq), transport.peer)
        self.assertTrue(transport.closed)
        with self.assertRaises(DomainError): await transport.receive()

    async def test_outbound_timestamps_padding_and_cleanup(self):
        sent = []
        class Socket:
            def sendto(self, data, peer): sent.append(data)
            def close(self): sent.append('closed')
        transport = RTPAudioTransport(); transport.socket=Socket(); transport.peer=('127.0.0.1',10000)
        transport.timestamp=100; transport.sequence=65535
        await transport.send_audio(b'\xff'*80, encoding='mulaw', turn_id='test')
        await transport.send_audio(b'\xff'*160, encoding='mulaw', turn_id='test')
        self.assertEqual(len(sent[0]),172)
        self.assertEqual(struct.unpack('!BBHII',sent[1][:12])[2:4],(0,260))
        await transport.close()
        self.assertEqual((await transport.receive())['event'],'disconnect')


class DemoTests(unittest.TestCase):
    def setUp(self): self.store=Store()
    def tearDown(self): self.store.close()

    def test_idempotent_seed_policy_two_dentists_and_reset_scope(self):
        first = seed_smilecare(self.store, mode='mock', clock=lambda:datetime(2030,10,8,tzinfo=timezone.utc))
        self.assertTrue(first['created'])
        self.assertFalse(seed_smilecare(self.store)['created'])
        self.assertEqual(self.store.count('appointments',TENANT),2)
        rows=self.store.list('appointments',TENANT)
        self.assertEqual(len({a['dentist_id'] for a in rows}),2)
        calendar=MockCalendarProvider(self.store)
        self.assertFalse(calendar.available(TENANT,rows[0]['starts_at'],30))
        self.assertFalse(calendar.available(TENANT,'2030-10-12T15:00:00+03:00',30))
        self.assertFalse(calendar.available(TENANT,'2030-10-14T18:00:00+03:00',30))
        self.assertTrue(calendar.available(TENANT,'2030-10-14T17:30:00+03:00',30))
        self.store.seed('other','other-admin')
        with self.assertRaises(DomainError): reset_smilecare(self.store,self.store.principal('other-admin','other'))
        reset_smilecare(self.store,self.store.principal('smilecare-demo-admin',TENANT))
        self.assertTrue(all(a['status']=='confirmed' for a in self.store.list('appointments',TENANT) if a.get('seeded_fixture')))
        self.assertEqual(self.store.get('assistants','other','default')['name'],'Assistant')

    def test_no_adoption_of_unmarked_tenant(self):
        self.store.seed(TENANT)
        with self.assertRaises(DomainError): seed_smilecare(self.store)


class ARITests(unittest.IsolatedAsyncioTestCase):
    def settings(self): return ARISettings('http://127.0.0.1:8088/ari','testmid','s'*32,'demo','default','demo-admin','127.0.0.1','127.0.0.1',bind_host='127.0.0.1')

    async def test_private_endpoint_required_and_auth_not_in_url(self):
        self.settings().validate()
        with self.assertRaises(DomainError): ARISettings('http://8.8.8.8:8088/ari','x','s'*32,'demo','default','demo-admin','127.0.0.1','127.0.0.1').validate()

    async def test_untrusted_route_is_ignored(self):
        manager=SimpleNamespace(store=SimpleNamespace(operations=Operations()), providers=SimpleNamespace(active_llms={}))
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda r:self.fail('Must not make ARI calls')),base_url='http://127.0.0.1/ari/')
        bridge=ARIBridge(self.settings(),manager,None,client=client)
        for application, extension, name in (('other','2000','PJSIP/1001-x'),('testmid-voice','9999','PJSIP/1001-x'),('testmid-voice','2000','PJSIP/9999-x')):
            await bridge.event({'application':application,'type':'StasisStart','channel':{'id':'caller','name':name,'dialplan':{'exten':extension}}})
        self.assertFalse(bridge.tasks)
        await bridge.close()

    async def test_synthetic_ari_lifecycle_owns_cleanup_and_call_persistence(self):
        from semantic_os.backend.assistant.providers import ProviderRegistry
        from semantic_os.backend.assistant.orchestration import Orchestrator
        from semantic_os.backend.assistant.voice import VoiceSessionManager
        from semantic_os.backend.assistant.asterisk import AsteriskTelephonyProvider
        store=Store(); store.seed(); store.operations=Operations()
        providers=ProviderRegistry(); providers.asterisk=AsteriskTelephonyProvider()
        providers.local_stt=SimpleNamespace(require=lambda locale:None)
        providers.local_tts=SimpleNamespace(capability=SimpleNamespace(locales=('bg-BG','en-US')))
        assistant=store.get('assistants','demo','default')
        store.update('assistants','demo','default',{'llm_provider':'qwen','voice_settings':{**assistant['voice_settings'],
            'telephony_provider':'asterisk','stt_provider':'faster_whisper','tts_provider':'piper'}})
        manager=VoiceSessionManager(store,providers,Orchestrator(store,providers))
        requests=[]
        def handler(request):
            requests.append((request.method,request.url.path))
            if request.url.path.endswith('/variable'):
                value='127.0.0.1' if request.url.params['variable']=='UNICASTRTP_LOCAL_ADDRESS' else '10000'
                return httpx.Response(200,json={'value':value})
            return httpx.Response(204)
        class Runtime:
            async def threaded(self, function, *args, **kwargs): return function(*args, **kwargs)
            async def run(self, actor, call, transport):
                self.call=call
                await transport.clear()  # No media is sent to an actual Asterisk peer in this contract test.
                manager.finish(actor,call['id'])
        runtime=Runtime()
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler),base_url='http://127.0.0.1:8088/ari/')
        bridge=ARIBridge(self.settings(),manager,runtime,client=client)
        await bridge.journey('synthetic-caller')
        call=store.list('call_sessions','demo')[0]
        self.assertEqual(call['status'],'ended')
        self.assertEqual(call['tenant_id'],'demo')
        self.assertEqual(store.get('conversations','demo',call['conversation_id'])['call_session_id'],call['id'])
        self.assertFalse(bridge.sessions)
        self.assertEqual(len([r for r in requests if r[0]=='DELETE']),3)
        await bridge.close(); store.close()


if __name__ == '__main__': unittest.main()
