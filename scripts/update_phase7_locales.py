"""Add bilingual labels to the existing Vue resource files."""
import json
import sys
from pathlib import Path
root = Path(__file__).resolve().parents[1]/'semantic_os/frontend/src/locales'
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.language import TEXT
labels = {
    'en-US': {'callActivity':'Call activity', 'agentExecutions':'Agent executions', 'toolExecutions':'Tool executions', 'llmTokens':'Reported LLM tokens', 'tokenUsageUnavailable':'Not reported by the provider',
        'available':'Available', 'unavailable':'Unavailable', 'appointment_created':'Appointment created', 'appointment_rescheduled':'Appointment rescheduled', 'appointment_cancelled':'Appointment cancelled', 'escalated':'Human follow-up requested',
        'mockNotice':'Default providers and the calendar are mocked. Configured self-hosted providers remain unverified until real model, audio and call tests pass.'},
    'bg-BG': {'callActivity':'Активност на обаждането', 'agentExecutions':'Изпълнения на агентите', 'toolExecutions':'Изпълнения на инструментите', 'llmTokens':'Отчетени токени на езиковия модел', 'tokenUsageUnavailable':'Не са отчетени от доставчика',
        'available':'Свободен час', 'unavailable':'Зает час', 'appointment_created':'Създаден час', 'appointment_rescheduled':'Преместен час', 'appointment_cancelled':'Отменен час', 'escalated':'Поискана връзка с оператор',
        'mockNotice':'Доставчиците по подразбиране и календарът са симулирани. Самостоятелно хостваните доставчици остават непроверени до успешни тестове с реален модел, аудио и обаждания.'}}
for locale, values in labels.items():
    path = root/(locale+'.json')
    data = json.loads(path.read_text(encoding='utf-8'))
    data.update(values)
    for key in ('invalid_model_output','generation_cancelled','invalid_model_checksum','invalid_model_manifest','model_license_required','inference_hardware_required','context_limit'):
        data[key] = TEXT[locale][key]
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
