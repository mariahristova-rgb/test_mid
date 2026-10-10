"""Keep frontend error/audit resources in sync with owned backend localization."""
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from semantic_os.backend.assistant.language import TEXT

AUDIT = {
    'en-US': {'assistant:created': 'Assistant created', 'assistant:configured': 'Assistant configured', 'agent:configured': 'Agent configured', 'message:received': 'Message received', 'approval:confirmed': 'Action confirmed', 'tenant:configured': 'Organization configured', 'connection:created': 'Channel connected', 'retention:redacted': 'Expired content redacted', 'reminder:dispatched': 'Reminder dispatched', 'reminder:failed': 'Reminder failed', 'template:configured': 'Template configured', 'membership:created': 'Member added', 'membership:configured': 'Membership configured', 'request:rejected': 'Request rejected', 'call:start': 'Call started', 'call:speak': 'Speech simulated', 'call:barge_in': 'Speech interrupted', 'call:finish_speaking': 'Speech finished', 'call:language': 'Call language changed', 'call:transcript': 'Transcript processed', 'call:transfer': 'Call transferred', 'call:terminate': 'Call ended', 'dateExample': '10/08/2030 02:30 PM'},
    'bg-BG': {'assistant:created': 'Създаден асистент', 'assistant:configured': 'Настроен асистент', 'agent:configured': 'Настроен агент', 'message:received': 'Получено съобщение', 'approval:confirmed': 'Потвърдено действие', 'tenant:configured': 'Настроена организация', 'connection:created': 'Свързан канал', 'retention:redacted': 'Заличено съдържание с изтекъл срок', 'reminder:dispatched': 'Изпратено напомняне', 'reminder:failed': 'Неуспешно напомняне', 'template:configured': 'Настроен шаблон', 'membership:created': 'Добавен член', 'membership:configured': 'Настроено членство', 'request:rejected': 'Отхвърлена заявка', 'call:start': 'Начало на обаждане', 'call:speak': 'Симулиран говор', 'call:barge_in': 'Прекъснат говор', 'call:finish_speaking': 'Завършен говор', 'call:language': 'Променен език на обаждането', 'call:transcript': 'Обработен текст', 'call:transfer': 'Прехвърлено обаждане', 'call:terminate': 'Приключило обаждане', 'dateExample': '08.10.2030 14:30'},
}
for locale in TEXT:
    path = ROOT / f'semantic_os/frontend/src/locales/{locale}.json'
    resources = json.loads(path.read_text(encoding='utf-8'))
    # Only error keys are shared: notification text keeps its distinct UI labels.
    for key in ('forbidden', 'not_found', 'unauthorized', 'invalid_input', 'conflict', 'unsupported_locale', 'unconfigured', 'rate_limited', 'budget_exceeded', 'invalid_signature', 'invalid_timezone', 'timezone_required', 'tool_denied', 'limit_reached', 'invalid_transition', 'provider_error', 'timeout'):
        resources[key] = TEXT[locale][key]
    resources.update(AUDIT[locale])
    resources['resume'] = 'Resume assistant' if locale == 'en-US' else 'Възобновяване на асистента'
    resources['conversation:resumed'] = 'Assistant resumed' if locale == 'en-US' else 'Възобновен асистент'
    path.write_text(json.dumps(resources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
