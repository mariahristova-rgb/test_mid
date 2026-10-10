"""Bilingual labels for messaging transport and inbox controls."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VALUES = {
 'en-US': {
  'all': 'All', 'takeover': 'Take over', 'closeConversation': 'Close conversation', 'humanReply': 'Human reply', 'human': 'Human operator', 'disableConnection': 'Disable connection', 'enableConnection': 'Enable connection', 'conversationDate': 'Conversation date',
  'approveDraft': 'Approve draft', 'attachment': 'Attachment (2 MB maximum)', 'attachmentLimit': 'Files must be no larger than 2 MB.',
  'quarantined': 'Quarantined pending review', 'draft': 'Draft', 'queued': 'Queued', 'retry': 'Retry scheduled', 'dead_letter': 'Needs review',
  'uncertain': 'Delivery uncertain — reconciliation required', 'cancelled': 'Cancelled', 'simulated': 'Simulated',
  'awaiting_customer': 'Awaiting customer', 'awaiting_agent': 'Awaiting agent', 'awaiting_approval': 'Awaiting approval', 'escalated': 'Escalated', 'resolved': 'Resolved', 'closed': 'Closed',
  'provider': 'Provider', 'mock': 'Mock provider', 'smtp': 'SMTP · unverified', 'meta': 'WhatsApp Cloud API · unverified', 'connectChannel': 'Configure channel',
  'sender_id': 'Configured sender address or number', 'public_origin': 'Public HTTPS origin', 'webhook_secret': 'Webhook secret',
  'app_secret': 'App secret', 'verify_token': 'Verification token', 'access_token': 'Access token', 'auth_token': 'Authentication token',
  'smtp_password': 'SMTP password', 'waba_id': 'WhatsApp Business account ID', 'phone_number_id': 'WhatsApp phone number ID',
  'api_version': 'Configured Graph API version', 'account_sid': 'Account SID', 'smtp_host': 'SMTP server', 'smtp_username': 'SMTP username', 'smtp_port': 'SMTP port',
  'enableLiveMessaging': 'Authorize live sends (also requires the server enable flag)', 'emailDraftRequired': 'Hold AI email responses for approval',
  'rate_per_minute': 'Maximum send attempts per minute', 'webhookStatus': 'Webhook verification', 'verified': 'Verified signature', 'unverified': 'Unverified',
  'lastError': 'Last connection error', 'capabilities': 'Capabilities', 'inbound': 'Inbound messages', 'outbox': 'Queued delivery', 'callbacks': 'Delivery callbacks',
  'providerSetupNotice': 'Mock connections send no real messages. Live adapters require tenant credentials, explicit enablement and separate end-to-end verification.',
  'mockNotice': 'Development foundation: the LLM, calendar and default channels are mocked. Live voice and messaging adapters require explicit configuration and verification.',
  'follow_up': 'Follow-up', 'human_escalation': 'Human escalation', 'appointment_rescheduled': 'Appointment rescheduling', 'appointment_cancelled': 'Appointment cancellation',
  'consent_required': 'Messaging consent is required.', 'template_required': 'An approved message template and consent are required.', 'unsupported_attachment': 'This attachment format is not supported.',
 },
 'bg-BG': {
  'all': 'Всички', 'takeover': 'Поемане от оператор', 'closeConversation': 'Затваряне на разговор', 'humanReply': 'Отговор от оператор', 'human': 'Оператор', 'disableConnection': 'Изключване на връзката', 'enableConnection': 'Включване на връзката', 'conversationDate': 'Дата на разговора',
  'approveDraft': 'Одобряване на чернова', 'attachment': 'Прикачен файл (до 2 MB)', 'attachmentLimit': 'Файлът трябва да е до 2 MB.',
  'quarantined': 'Под карантина до преглед', 'draft': 'Чернова', 'queued': 'В опашката', 'retry': 'Планиран повторен опит', 'dead_letter': 'Необходим е преглед',
  'uncertain': 'Неясна доставка — необходима е проверка', 'cancelled': 'Отменен', 'simulated': 'Симулирано',
  'awaiting_customer': 'Изчаква клиент', 'awaiting_agent': 'Изчаква агент', 'awaiting_approval': 'Изчаква одобрение', 'escalated': 'Предаден на оператор', 'resolved': 'Разрешен', 'closed': 'Затворен',
  'provider': 'Доставчик', 'mock': 'Симулиран доставчик', 'smtp': 'SMTP · непроверен', 'meta': 'WhatsApp Cloud API · непроверен', 'connectChannel': 'Настройка на канал',
  'sender_id': 'Настроен адрес или номер на подателя', 'public_origin': 'Публичен HTTPS адрес', 'webhook_secret': 'Тайна за уебхука',
  'app_secret': 'Тайна на приложението', 'verify_token': 'Токен за проверка', 'access_token': 'Токен за достъп', 'auth_token': 'Токен за удостоверяване',
  'smtp_password': 'Парола за SMTP', 'waba_id': 'Идентификатор на WhatsApp Business профила', 'phone_number_id': 'Идентификатор на WhatsApp номера',
  'api_version': 'Настроена версия на Graph API', 'account_sid': 'Идентификатор на профила', 'smtp_host': 'SMTP сървър', 'smtp_username': 'SMTP потребител', 'smtp_port': 'SMTP порт',
  'enableLiveMessaging': 'Разрешаване на реални съобщения (изисква и настройка на сървъра)', 'emailDraftRequired': 'Задържане на AI имейлите за одобрение',
  'rate_per_minute': 'Максимален брой опити за изпращане в минута', 'webhookStatus': 'Проверка на уебхука', 'verified': 'Проверен подпис', 'unverified': 'Непроверен',
  'lastError': 'Последна грешка на връзката', 'capabilities': 'Възможности', 'inbound': 'Входящи съобщения', 'outbox': 'Доставка от опашката', 'callbacks': 'Потвърждения за доставка',
  'providerSetupNotice': 'Симулираните връзки не изпращат реални съобщения. Реалните адаптери изискват данни за достъп, изрично разрешение и отделна цялостна проверка.',
  'mockNotice': 'Среда за разработка: езиковият модел, календарът и основните канали са симулирани. Реалните гласови и съобщителни адаптери изискват изрична настройка и проверка.',
  'follow_up': 'Последваща задача', 'human_escalation': 'Предаване на оператор', 'appointment_rescheduled': 'Преместване на час', 'appointment_cancelled': 'Отмяна на час',
  'consent_required': 'Необходимо е съгласие за съобщения.', 'template_required': 'Необходими са одобрен шаблон и съгласие.', 'unsupported_attachment': 'Този файлов формат не се поддържа.',
 }
}
for locale, values in VALUES.items():
    path = ROOT / f'semantic_os/frontend/src/locales/{locale}.json'
    resources = json.loads(path.read_text(encoding='utf-8'))
    resources.update(values)
    path.write_text(json.dumps(resources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
