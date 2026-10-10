"""Reproducible four-scenario demonstration using the same signed acceptance fixtures."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.tests.test_messaging import MessagingAcceptance

SCENARIOS = {
    'A_bulgarian_whatsapp_booking': 'test_bulgarian_whatsapp_booking_and_duplicate_action',
    'B_english_email_next_monday': 'test_english_email_next_monday_thread_and_draft',
    'C_bulgarian_sms_reminder': 'test_bulgarian_sms_reminder_segments_callback_and_duplicate',
    'D_human_handoff': 'test_customer_human_intent_assigns_and_pauses',
    'D_operator_reply_resume_close': 'test_human_takeover_pauses_agent_and_reply_resume_close',
}

def demo():
    result = {'mode': 'MOCK', 'timezone': 'Europe/Sofia', 'live_delivery_verified': False, 'scenarios': {}}
    for name, test in SCENARIOS.items():
        fixture = MessagingAcceptance(test)
        fixture.setUp()
        try:
            getattr(fixture, test)()
            store = fixture.store
            result['scenarios'][name] = {'verified': True,
                'appointments': [{k: row[k] for k in ('starts_at', 'locale', 'status')} for row in store.list('appointments', 'demo')],
                'messages': [{k: row[k] for k in ('channel', 'direction', 'content', 'active_locale', 'delivery_status')} for row in store.list('messages', 'demo')],
                'handoffs': [row['handoff'] for row in store.list('agent_executions', 'demo')],
                'jobs': [{k: row[k] for k in ('kind', 'status')} for row in store.list('jobs', 'demo')]}
        finally:
            fixture.tearDown()
    return result

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    content = json.dumps(demo(), ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(content + '\n', encoding='utf-8')
        print('All four offline scenarios verified; demonstration artifact written.')
    else:
        print(content)
