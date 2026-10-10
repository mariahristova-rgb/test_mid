"""Synthetic telephony/media acceptance. No real calls, credentials, or speech-provider requests."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import io
import json
import secrets
import struct
import tempfile
from pathlib import Path
import time
import unittest
from urllib.parse import urlencode
import wave
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.audio import TurnBuffer, mulaw_to_pcm, pcm_to_mulaw
from semantic_os.backend.assistant.domain import AudioFrame, DomainError, VoiceConfig
from semantic_os.backend.assistant.live_voice import AzureSpeechProvider, TwilioTelephonyProvider, stream_twiml
from semantic_os.backend.assistant.store import Store, uid


class VoiceAcceptance(unittest.TestCase):
    def setUp(self):
        self.store = Store()
        self.now = datetime(2030, 10, 8, 9, 0, tzinfo=timezone.utc)
        self.app = create_app(store=self.store, demo_enabled=True, demo_token='synthetic-voice-session',
                              encryption_key=Fernet.generate_key().decode(), clock=lambda: self.now)
        self.client = TestClient(self.app)
        self.headers = {'Authorization': 'Bearer synthetic-voice-session'}
        self.voice, self.gateway = self.app.state.voice, self.app.state.voice_gateway
        self.actor = self.store.principal('demo-admin', 'demo')

    def tearDown(self):
        self.client.close()
        self.app.state.voice_runtime.shutdown()
        self.store.close()

    def call(self, locale=None, **kwargs):
        result = self.client.post('/api/calls', headers=self.headers, json={'locale': locale, **kwargs})
        self.assertEqual(result.status_code, 201, result.text)
        return result.json()

    def event(self, call, action, **kwargs):
        return self.client.post('/api/calls/' + call['id'] + '/events', headers=self.headers,
            json={'action': action, 'event_id': kwargs.pop('event_id', uid()), **kwargs})

    def ticket(self, call):
        response = self.client.post('/api/calls/' + call['id'] + '/stream-ticket', headers=self.headers, json={'confirmed': True})
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()['ticket']

    def until(self, socket, name):
        for _ in range(50):
            event = socket.receive_json()
            if event['event'] == 'error': self.fail(event)
            if event['event'] == name: return event
        self.fail('Expected transport event ' + name)

    def recognition(self, socket, text, id, final=True):
        socket.send_json({'event': 'recognition', 'text': text, 'utterance_id': id, 'final': final})
        return self.until(socket, 'turn_result') if final else self.until(socket, 'partial_ignored')

    def connection(self):
        secret = secrets.token_urlsafe(32)  # Per-test ephemeral signing material, never a stored credential.
        response = self.client.post('/api/telephony/connections', headers=self.headers,
            json={'phone_number': '+359888000001', 'webhook_secret': secret})
        self.assertEqual(response.status_code, 201, response.text)
        self.assertNotIn(secret, response.text)
        return response.json(), secret

    def signed_incoming(self, connection, secret, **updates):
        payload = {'call_id': 'provider-fixture-1', 'from': '+359888123456', 'to': '+359888000001',
                   'status': 'ringing', 'event_id': 'incoming-1', **updates}
        raw = json.dumps(payload).encode()
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        return self.client.post('/webhooks/telephony/demo/' + connection['id'], content=raw, headers={'X-Signature': signature})

    def test_signed_incoming_routing_and_duplicate(self):
        connection, secret = self.connection()
        first = self.signed_incoming(connection, secret)
        self.assertEqual(first.status_code, 200, first.text)
        second = self.signed_incoming(connection, secret)
        self.assertEqual(first.json()['id'], second.json()['id'])
        self.assertEqual(self.store.count('call_sessions', 'demo'), 1)
        self.assertEqual(first.json()['provider_call_id'], 'provider-fixture-1')
        self.assertNotIn('+359888123456', first.text)
        self.assertEqual(self.store.count('call_participants', 'demo'), 2)

    def test_invalid_signature_and_wrong_number_denied(self):
        connection, secret = self.connection()
        self.assertEqual(self.client.post('/webhooks/telephony/demo/' + connection['id'], json={}).status_code, 401)
        self.assertEqual(self.signed_incoming(connection, secret, to='+359888000002').status_code, 403)
        self.assertEqual(self.store.count('call_sessions', 'demo'), 0)

    def test_duration_usage_and_status_callback_once(self):
        connection, secret = self.connection()
        call = self.signed_incoming(connection, secret).json()
        self.now += timedelta(seconds=75)
        result = self.signed_incoming(connection, secret, status='completed', event_id='completed-1')
        self.assertEqual(result.json()['duration_seconds'], 75)
        self.signed_incoming(connection, secret, status='completed', event_id='completed-1')
        self.assertEqual(self.store.count('call_usage', 'demo'), 1)
        self.assertEqual(self.store.get('call_sessions', 'demo', call['id'])['status'], 'ended')

    def test_bulgarian_and_english_voice_booking_same_agents(self):
        for locale, texts in [('bg-BG', ['Искам да запиша час за утре в 15:00.', 'Казвам се Иван Иванов.', 'Да, потвърждавам.']),
                              ('en-US', ['I would like to book tomorrow at 16:00.', 'My name is John Smith.', 'Yes, confirm.'])]:
            call = self.call(locale)
            self.assertIn('Здравейте!' if locale == 'bg-BG' else 'Hello!', call['last_response'])
            for index, text in enumerate(texts):
                response = self.event(call, 'transcript', text=text, utterance_id=f'{locale}-{index}')
                self.assertEqual(response.status_code, 200, response.text)
            self.assertIn('Часът е потвърден' if locale == 'bg-BG' else 'Appointment confirmed', response.json()['last_response'])
            trace = self.store.list('agent_executions', 'demo', call['conversation_id'])
            self.assertTrue(trace)
            self.assertTrue(all(x['handoff']['locale'] == locale for x in trace))
            messages = self.store.list('messages', 'demo', call['conversation_id'])
            self.assertTrue(all(x['content'] == '' for x in messages))
        self.assertEqual(self.store.count('appointments', 'demo'), 2)

    def test_partial_and_corrected_finals_do_not_repeat_tools(self):
        call = self.call('bg-BG')
        self.event(call, 'transcript', text='Искам да запиша час за утре в 15:00.', utterance_id='u1', final=False)
        self.assertEqual(self.store.count('tool_executions', 'demo'), 0)
        self.event(call, 'transcript', text='Искам да запиша час за утре в 15:00.', utterance_id='u1')
        correction = self.event(call, 'transcript', text='Искам да запиша час за утре в 16:00.', utterance_id='u1')
        self.assertTrue(correction.json()['correction_ignored'])
        self.assertEqual(self.store.count('tool_executions', 'demo'), 1)
        self.event(call, 'transcript', text='Иван Иванов', utterance_id='u2')
        self.event(call, 'transcript', text='Да, потвърждавам.', utterance_id='u3')
        self.event(call, 'transcript', text='Да, потвърждавам.', utterance_id='u3')
        self.assertEqual(self.store.count('appointments', 'demo'), 1)

    def test_stream_media_pipeline_both_languages(self):
        call = self.call('bg-BG')
        token = self.ticket(call)
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': token})
            self.until(socket, 'ready')
            self.until(socket, 'audio_done')
            for index, text in enumerate(['Искам да запиша час за утре в 15:00.', 'Иван Иванов', 'Да, потвърждавам.']):
                socket.send_json({'event': 'media', 'frame': {'sequence': index, 'utterance_id': str(index),
                    'payload': base64.b64encode(text.encode()).decode(), 'encoding': 'fixture_utf8', 'final': True}})
                result = self.until(socket, 'turn_result')
                self.until(socket, 'audio_done')
            self.assertIn('Часът е потвърден', result['response'])
            socket.send_json({'event': 'stop'})
        self.assertEqual(self.store.count('appointments', 'demo'), 1)

    def test_one_use_ticket_and_cross_tenant_binding(self):
        call = self.call()
        token = self.ticket(call)
        self.store.seed('other', 'other')
        actor, bound, _ = self.gateway.consume_ticket(token)
        self.assertEqual(actor.tenant_id, 'demo')
        self.assertEqual(bound['id'], call['id'])
        with self.assertRaises(DomainError): self.gateway.consume_ticket(token)
        other = self.store.principal('other', 'other')
        with self.assertRaises(DomainError): self.gateway.ticket(other, call['id'])
        self.assertNotIn(token, json.dumps(self.store.list('voice_tickets', 'demo')))

    def test_expired_ticket_rejected(self):
        token = self.ticket(self.call())
        self.now += timedelta(seconds=61)
        with self.assertRaises(DomainError): self.gateway.consume_ticket(token)

    def test_language_switch_and_human_transfer(self):
        call = self.call('bg-BG')
        switched = self.event(call, 'transcript', text='Премини на английски', utterance_id='lang')
        self.assertEqual(switched.json()['voice_locale'], 'en-US')
        self.event(call, 'transcript', text='I need a human', utterance_id='human')
        response = self.event(call, 'transcript', text='Yes, confirm.', utterance_id='confirm-human')
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()['status'], 'transferred')
        self.assertEqual(self.store.count('follow_up_tasks', 'demo'), 1)
        self.assertEqual(self.store.count('call_usage', 'demo'), 1)

    def test_first_turn_detects_language_without_changing_later_ambiguous_text(self):
        call = self.call()
        result = self.event(call, 'transcript', text='Hello', utterance_id='first')
        self.assertEqual(result.json()['voice_locale'], 'en-US')
        result = self.event(call, 'transcript', text='123', utterance_id='ambiguous')
        self.assertEqual(result.json()['voice_locale'], 'en-US')

    def test_cross_tenant_call_events_and_transcripts_denied(self):
        call = self.call()
        self.store.seed('other', 'other')
        other = self.store.principal('other', 'other')
        with self.assertRaises(DomainError): self.voice.event(other, call['id'], 'terminate')
        with self.assertRaises(DomainError): self.voice.process_text(other, call['id'], 'Hello', 'u1')

    def test_recording_and_transcript_consent_encryption_retention(self):
        config = VoiceConfig(recording=True, transcript_storage=True, lawful_basis='consent', transcript_retention_days=1)
        self.store.update('assistants', 'demo', 'default', {'voice_settings': config.model_dump(mode='json')})
        self.store.update_tenant('demo', {**self.store.tenant('demo'), 'recording_enabled': True, 'transcripts_enabled': True})
        call = self.call()  # Configuration permits recording but cannot enable it silently.
        self.assertFalse(call['recording_enabled'])
        self.event(call, 'transcript', text='Съгласен съм със запис', utterance_id='consent')
        call = self.store.get('call_sessions', 'demo', call['id'])
        self.assertTrue(call['recording_enabled'])
        self.voice.record_audio(self.actor, call, 'Български адрес'.encode(), 'fixture_utf8', 8000)
        self.event(call, 'transcript', text='Здравейте', utterance_id='text')
        self.assertNotIn('Български адрес', json.dumps(self.store.list('voice_recordings', 'demo')))
        self.assertNotIn('Здравейте', json.dumps(self.store.list('voice_transcripts', 'demo')))
        content = self.client.get('/api/calls/' + call['id'] + '/transcripts', headers=self.headers).json()
        self.assertTrue(any('Здравейте' in x['content'] for x in content))
        self.now += timedelta(days=2)
        count = self.voice.purge_expired(self.actor)
        self.assertGreater(count, 0)
        self.assertEqual(self.client.get('/api/calls/' + call['id'] + '/transcripts', headers=self.headers).json(), [])

    def test_abuse_limit_and_destination_allowlist(self):
        cfg = VoiceConfig(max_concurrent_calls=1)
        self.store.update('assistants', 'demo', 'default', {'voice_settings': cfg.model_dump(mode='json')})
        call = self.call()
        self.assertEqual(self.client.post('/api/calls', headers=self.headers, json={}).status_code, 429)
        self.assertEqual(self.event(call, 'transfer', destination='+359888999999').status_code, 403)

    def test_audio_reader_stays_responsive_during_slow_agent_and_barge_in(self):
        original = self.app.state.providers.llm.reply
        def slow(*args):
            time.sleep(.4)
            return original(*args)
        self.app.state.providers.llm.reply = slow
        call = self.call('en-US')
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': self.ticket(call)})
            self.until(socket, 'ready'); self.until(socket, 'audio_done')
            socket.send_json({'event': 'recognition', 'text': 'Hello', 'utterance_id': 'slow'})
            time.sleep(.15)
            start = time.monotonic()
            socket.send_json({'event': 'barge_in'})
            self.until(socket, 'clear')
            socket.send_json({'event': 'ping'})
            self.until(socket, 'pong')
            self.assertLess(time.monotonic() - start, .25)
            self.until(socket, 'turn_result')
            socket.send_json({'event': 'stop'})

    def test_stream_provider_failure_has_safe_error_and_no_retry(self):
        def failed(*args): raise DomainError('provider_error', 502)
        self.app.state.providers.llm.reply = failed
        call = self.call('en-US')
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': self.ticket(call)})
            self.until(socket, 'ready'); self.until(socket, 'audio_done')
            socket.send_json({'event': 'recognition', 'text': 'Hello', 'utterance_id': 'failed'})
            result = socket.receive_json()
            self.assertEqual(result['event'], 'error')
            self.assertEqual(result['code'], 'provider_error')
        self.assertEqual(self.store.count('tool_executions', 'demo'), 0)

    def test_silent_traffic_does_not_expire_an_active_slow_turn(self):
        original=self.app.state.providers.llm.reply
        def slow(*args):
            time.sleep(.5)
            return original(*args)
        self.app.state.providers.llm.reply=slow
        original_config=self.voice.config
        self.voice.config=lambda *args: original_config(*args).model_copy(update={'silence_timeout_seconds':.2})
        call=self.call('en-US')
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event':'start','ticket':self.ticket(call)})
            self.until(socket,'ready'); self.until(socket,'audio_done')
            socket.send_json({'event':'recognition','text':'Hello','utterance_id':'slow-idle'})
            for _ in range(12):
                time.sleep(.04)
                socket.send_json({'event':'ping'})
                self.until(socket,'pong')
            self.until(socket,'turn_result')
            self.until(socket,'audio_done')
            socket.send_json({'event':'stop'})
        self.assertEqual(self.store.get('call_sessions','demo',call['id'])['status'],'ended')

    def test_provider_failure_plays_cached_audio_without_retrying_tts_or_tools(self):
        def failed(*args): raise DomainError('provider_error',502)
        self.app.state.providers.llm.reply=failed
        self.voice.cached_prompts[('mock','en-US','mock-en','slow')]=b'\xff'*320
        call=self.call('en-US')
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event':'start','ticket':self.ticket(call)})
            self.until(socket,'ready'); self.until(socket,'audio_done')
            socket.send_json({'event':'recognition','text':'Hello','utterance_id':'failure-cache'})
            error=socket.receive_json()
            self.assertEqual(error['event'],'error')
            self.assertEqual(error['code'],'provider_error')
            packet=self.until(socket,'audio')
            self.assertEqual(packet['encoding'],'mulaw')
            self.assertTrue(packet['turn_id'].startswith('failure:'))
            self.assertFalse(packet['speech_validated'])
        self.assertEqual(self.store.count('tool_executions','demo'),0)

    def test_voice_tool_permission_and_unsupported_language_config(self):
        call = self.call('bg-BG')
        self.store.update('agents', 'demo', 'executor', {'allowed_tools': []})
        result = self.event(call, 'transcript', text='Искам да запиша час за утре в 15:00.', utterance_id='denied')
        self.assertEqual(result.status_code, 403)
        self.assertEqual(self.store.count('appointments', 'demo'), 0)
        config = self.client.get('/api/assistants', headers=self.headers).json()[0]
        id = config.pop('id'); config.pop('tenant_id')
        config['voice_settings']['voices']['bg-BG'] = 'mock-en'
        response = self.client.put('/api/assistants/' + id, headers=self.headers, json=config)
        self.assertEqual(response.status_code, 422)

    def test_revoked_membership_blocks_stream_ticket(self):
        token = self.ticket(self.call())
        self.store.update('users', 'demo', self.actor.user_id, {'enabled': False})
        with self.assertRaises(DomainError): self.gateway.consume_ticket(token)

    def test_silence_timeout_and_call_duration_persist(self):
        call = self.call('en-US')
        original = self.voice.config
        self.voice.config = lambda *args: original(*args).model_copy(update={'silence_timeout_seconds': .05})
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': self.ticket(call)})
            self.until(socket, 'ready'); self.until(socket, 'audio_done')
            event = socket.receive_json()
            self.assertEqual(event['code'], 'timeout')
        time.sleep(.1)
        self.assertEqual(self.store.get('call_sessions', 'demo', call['id'])['status'], 'failed')
        self.assertEqual(self.store.count('call_usage', 'demo'), 1)

    def test_late_inflight_response_does_not_reopen_timed_out_call(self):
        original = self.app.state.providers.llm.reply
        def slow(*args):
            time.sleep(.7)
            return original(*args)
        self.app.state.providers.llm.reply = slow
        cfg = VoiceConfig(max_latency_ms=500)
        self.store.update('assistants', 'demo', 'default', {'voice_settings': cfg.model_dump(mode='json')})
        call = self.call('en-US')
        with self.client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': self.ticket(call)})
            self.until(socket, 'ready'); self.until(socket, 'audio_done')
            socket.send_json({'event': 'recognition', 'text': 'Hello', 'utterance_id': 'slow-timeout'})
            result = socket.receive_json()
            self.assertEqual(result['code'], 'timeout')
        time.sleep(.4)
        self.assertEqual(self.store.get('call_sessions', 'demo', call['id'])['status'], 'failed')
        self.assertEqual(self.store.count('call_usage', 'demo'), 1)

    def test_voice_session_survives_database_reopen(self):
        with tempfile.TemporaryDirectory() as directory:
            store = Store(str(Path(directory) / 'voice.sqlite3'))
            app = create_app(store=store, demo_enabled=True, demo_token='synthetic-reopen-session')
            actor = store.principal('demo-admin', 'demo')
            call = app.state.voice.start(actor, 'default', 'bg-BG')
            app.state.voice.event(actor, call['id'], 'transcript', text='Здравейте', event_id='hello')
            app.state.voice_runtime.shutdown(); store.close()
            reopened = Store(str(Path(directory) / 'voice.sqlite3'))
            self.assertEqual(reopened.get('call_sessions', 'demo', call['id'])['voice_locale'], 'bg-BG')
            self.assertEqual(reopened.count('call_events', 'demo'), 2)
            self.assertTrue(reopened.get('conversations', 'demo', call['conversation_id']))
            reopened.close()

    def test_unattached_call_timeout_is_not_left_active(self):
        call = self.call()
        self.now += timedelta(seconds=601)
        self.assertEqual(self.voice.expire_idle_calls(), 1)
        self.assertEqual(self.store.get('call_sessions', 'demo', call['id'])['error_code'], 'timeout')
        self.assertEqual(self.voice.expire_idle_calls(), 0)

    def test_declined_transfer_cannot_later_transfer_on_stale_confirmation(self):
        call = self.call('en-US')
        self.event(call, 'transcript', text='I need a human', utterance_id='human')
        self.event(call, 'transcript', text='No', utterance_id='decline')
        response = self.event(call, 'transcript', text='Yes, confirm.', utterance_id='later')
        self.assertEqual(response.json()['status'], 'listening')
        self.assertEqual(self.store.count('follow_up_tasks', 'demo'), 0)

    def test_forward_voice_migration_preserves_legacy_session_data(self):
        call = self.call()
        legacy = {'id': call['id'], 'tenant_id': 'demo', 'assistant_id': 'default',
                  'conversation_id': call['conversation_id'], 'provider': 'mock', 'status': 'listening',
                  'voice_locale': 'bg-BG', 'transcripts': ['synthetic legacy transcript'],
                  'events': [{'event': 'start', 'at': '2030-10-08T09:00:00+00:00'}]}
        # Simulated v2 fixture only: never run these DDL statements on an actual workspace.
        with self.store.transaction():
            for table in ('call_events', 'call_participants', 'call_usage', 'voice_tickets', 'voice_transcripts', 'voice_recordings'):
                self.store.db.execute('DROP TABLE ' + table)
            self.store.db.execute('DELETE FROM schema_migrations WHERE version=3')
            self.store.db.execute('UPDATE call_sessions SET data=? WHERE tenant_id=? AND id=?',
                                  (json.dumps(legacy), 'demo', call['id']))
        self.store.migrate()
        restored = self.store.get('call_sessions', 'demo', call['id'])
        self.assertEqual(restored['transcripts'], legacy['transcripts'])
        self.assertEqual(restored['started_at'], legacy['events'][0]['at'])
        self.store.migrate()
        self.assertEqual(self.store.db.execute('SELECT count(*) FROM schema_migrations').fetchone()[0], 5)


class CodecAndLiveContracts(unittest.TestCase):
    def test_mulaw_silence_signs_and_vad_turn(self):
        self.assertEqual(mulaw_to_pcm(b'\xff' * 160), b'\x00\x00' * 160)
        pcm = struct.pack('<hhh', -1000, 0, 1000)
        decoded = struct.unpack('<hhh', mulaw_to_pcm(pcm_to_mulaw(pcm)))
        self.assertLess(decoded[0], 0); self.assertEqual(decoded[1], 0); self.assertGreater(decoded[2], 0)
        buffer = TurnBuffer(silence_ms=100)
        speech = struct.pack('<h', 2000) * 800
        result, active = buffer.feed(AudioFrame(sequence=1, utterance_id='u', encoding='pcm16',
                                               payload=base64.b64encode(speech).decode()))
        self.assertTrue(active); self.assertIsNone(result)
        result, _ = buffer.feed(AudioFrame(sequence=2, utterance_id='u', encoding='pcm16',
                                           payload=base64.b64encode(b'\0' * 1600).decode()))
        self.assertIsNotNone(result)

    def test_audio_bound_and_invalid_base64(self):
        buffer = TurnBuffer(max_seconds=1)
        with self.assertRaises(DomainError): buffer.feed(AudioFrame(sequence=1, utterance_id='u', payload='not-base64'))
        data = struct.pack('<h', 2000) * 8000
        buffer.feed(AudioFrame(sequence=1, utterance_id='u', encoding='pcm16', payload=base64.b64encode(data).decode()))
        with self.assertRaises(DomainError): buffer.feed(AudioFrame(sequence=2, utterance_id='u', encoding='pcm16', payload=base64.b64encode(data).decode()))

    def test_twilio_official_form_signature_and_disabled_network(self):
        provider = TwilioTelephonyProvider('AC' + '0' * 32, 'synthetic-auth-token', enabled=False)
        url = 'https://fixture.example.invalid/webhooks/telephony/demo/id'
        fields = {'CallSid': 'CA' + '0' * 32, 'To': '+359888000001'}
        body = urlencode(fields).encode()
        value = url + ''.join(k + v for k, v in sorted(fields.items()))
        signature = base64.b64encode(hmac.new(b'synthetic-auth-token', value.encode(), hashlib.sha1).digest()).decode()
        self.assertTrue(provider.verify_webhook(url, body, signature))
        self.assertFalse(provider.verify_webhook(url, body + b'&To=other', signature))
        with self.assertRaises(DomainError): provider.terminate('CA' + '0' * 32)
        self.assertIn('<Connect><Stream', stream_twiml('https://fixture.example.invalid', 'synthetic-ticket'))
        self.assertNotIn('?ticket=', stream_twiml('https://fixture.example.invalid', 'synthetic-ticket'))

    def test_azure_pcm_ssml_locale_and_no_real_requests(self):
        requests = []
        def fake(url, body, headers):
            requests.append((url, body, headers))
            if '/stt/' in url:
                with wave.open(io.BytesIO(body), 'rb') as wav:
                    self.assertEqual(wav.getframerate(), 16000)
                return json.dumps({'RecognitionStatus': 'Success', 'DisplayText': 'Здравейте'}).encode()
            return b'fixture-mulaw'
        provider = AzureSpeechProvider('synthetic-key', 'fixture-resource', 'westeurope', enabled=True, http=fake)
        self.assertEqual(provider.transcribe(b'\0' * 320, 'bg-BG'), 'Здравейте')
        provider.synthesize('Борис, ул. Иван Вазов & +359888000001', 'bg-BG', 'bg-BG-KalinaNeural')
        self.assertIn('&amp;', requests[-1][1].decode())
        self.assertFalse(provider.capability.speech_validated)
        with self.assertRaises(DomainError): provider.synthesize('text', 'bg-BG', 'en-US-JennyNeural')
        blocked = AzureSpeechProvider('synthetic-key', 'fixture-resource', 'westeurope')
        with self.assertRaises(DomainError): blocked.transcribe(b'\0' * 320, 'bg-BG')


if __name__ == '__main__': unittest.main(verbosity=2)
