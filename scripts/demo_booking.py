"""Deterministic API demonstration. Fictional names, in-memory state, no external calls."""
from datetime import datetime, timezone
import json
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store


def demo(locale):
    reference = datetime(2030, 10, 8, 9, 0, tzinfo=timezone.utc)
    store = Store()
    app = create_app(store=store, demo_enabled=True, demo_token='synthetic-demo-session', clock=lambda: reference)
    headers = {'Authorization': 'Bearer synthetic-demo-session'}
    messages = (['Здравейте, искам да запиша час за утре в 15:00.', 'Казвам се Иван Иванов.', 'Да, потвърждавам.']
                if locale == 'bg-BG' else ['Hello, I would like to book an appointment for tomorrow at 15:00.', 'My name is John Smith.', 'Yes, confirm.'])
    with TestClient(app) as client:
        conversation = client.post('/api/conversations', headers=headers, json={}).json()
        id = conversation['id']
        turns = []
        for index, content in enumerate(messages):
            response = client.post(f'/api/conversations/{id}/messages', headers=headers,
                                   json={'content': content, 'event_id': f'demo-{index}'})
            if response.status_code != 200:
                raise RuntimeError('Mock demonstration failed: ' + str(response.status_code))
            result = response.json()
            turns.append({'customer': content, 'assistant': result['response'], 'locale': result['locale'],
                          'stage': result['booking_status']})
        execution = client.get(f'/api/conversations/{id}/executions', headers=headers).json()
        appointments = client.get('/api/appointments', headers=headers).json()
        return {'locale': locale, 'timezone': 'Europe/Sofia', 'reference_at': reference.isoformat(),
                'provider_state': 'MOCK', 'turns': turns, 'appointment_count': len(appointments),
                'starts_at': appointments[0]['starts_at'],
                'handoffs': [{'intent': x['handoff']['intent'], 'locale': x['handoff']['locale'],
                             'source': x['handoff']['source_agent'], 'target': x['handoff']['target_agent'], 'phase': x['phase']} for x in execution['agents']],
                'tools': [x['tool'] for x in execution['tools']]}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', help='Optional UTF-8 artifact path inside test_mid')
    args = parser.parse_args()
    result = json.dumps([demo('bg-BG'), demo('en-US')], ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output).resolve()
        if not output.is_relative_to(Path(__file__).resolve().parents[1]):
            raise ValueError('Demonstration artifacts must stay inside test_mid')
        output.write_text(result + '\n', encoding='utf-8')
        print('Synthetic bilingual demonstration saved.')
    else:
        sys.stdout.reconfigure(encoding='utf-8')
        print(result)
