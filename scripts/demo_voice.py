"""Signed incoming call → synthetic audio → shared agents → TTS fixture, in both languages."""
import argparse
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store


def demo(locale):
    store = Store()
    reference = datetime(2030, 10, 8, 9, 0, tzinfo=timezone.utc)
    app = create_app(store=store, demo_enabled=True, demo_token='synthetic-demo-voice',
        encryption_key=Fernet.generate_key().decode(), clock=lambda: reference)
    headers = {'Authorization': 'Bearer synthetic-demo-voice'}
    secret = 'synthetic-demo-voice-webhook-secret'
    with TestClient(app) as client:
        assistant = client.get('/api/assistants', headers=headers).json()[0]
        id = assistant.pop('id'); assistant.pop('tenant_id')
        assistant['voice_settings']['locale'] = locale
        client.put('/api/assistants/' + id, headers=headers, json=assistant).raise_for_status()
        connection = client.post('/api/telephony/connections', headers=headers,
            json={'phone_number': '+359888000001', 'webhook_secret': secret}).json()
        raw = json.dumps({'call_id': 'synthetic-provider-call', 'from': '+359888123456', 'to': '+359888000001',
                          'status': 'ringing', 'event_id': 'incoming'}).encode()
        signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
        call = client.post('/webhooks/telephony/demo/' + connection['id'], content=raw, headers={'X-Signature': signature}).json()
        ticket = client.post('/api/calls/' + call['id'] + '/stream-ticket', headers=headers, json={'confirmed': True}).json()['ticket']
        texts = ['Искам да запиша час за утре в 15:00.', 'Казвам се Иван Иванов.', 'Да, потвърждавам.'] if locale == 'bg-BG' else [
                 'I would like to book an appointment for tomorrow at 15:00.', 'My name is John Smith.', 'Yes, confirm.']
        turns = []
        def until(socket, name):
            for _ in range(40):
                value = socket.receive_json()
                if value['event'] == 'error': raise RuntimeError('Synthetic voice demo failed')
                if value['event'] == name: return value
            raise RuntimeError('Missing stream event')
        with client.websocket_connect('/voice/media') as socket:
            socket.send_json({'event': 'start', 'ticket': ticket})
            until(socket, 'ready')
            greeting = until(socket, 'audio')
            until(socket, 'audio_done')
            for index, text in enumerate(texts):
                socket.send_json({'event': 'media', 'frame': {'sequence': index, 'utterance_id': f'utterance-{index}',
                    'payload': base64.b64encode(text.encode()).decode(), 'encoding': 'fixture_utf8', 'final': True}})
                reply = until(socket, 'turn_result')
                synthesized = until(socket, 'audio')
                until(socket, 'audio_done')
                turns.append({'caller': text, 'reply': reply['response'], 'locale': reply['locale'],
                    'synthetic_tts_roundtrip': base64.b64decode(synthesized['media']['payload']).decode() == reply['response']})
            socket.send_json({'event': 'stop'})
        appointment = client.get('/api/appointments', headers=headers).json()[0]
        trace = client.get('/api/conversations/' + call['conversation_id'] + '/executions', headers=headers).json()
        return {'locale': locale, 'timezone': 'Europe/Sofia', 'reference_at': reference.isoformat(),
            'state': 'MOCK', 'speech_validated': False, 'greeting': base64.b64decode(greeting['media']['payload']).decode(),
            'turns': turns, 'appointment_count': 1, 'starts_at': appointment['starts_at'],
            'tools': [row['tool'] for row in trace['tools']], 'handoff_locales': [row['handoff']['locale'] for row in trace['agents']],
            'transcripts_stored': store.count('voice_transcripts', 'demo')}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    target = Path(args.output).resolve()
    if not target.is_relative_to(Path(__file__).resolve().parents[1]): raise ValueError('Output must stay in test_mid')
    target.write_text(json.dumps([demo('bg-BG'), demo('en-US')], ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('Synthetic bilingual voice demonstration saved; no real calls or real speech requests.')
