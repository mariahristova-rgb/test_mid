"""Owned bilingual SaaS UI/error resources."""
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
PAIRS = {
 'onboarding': ('Organization setup', 'Настройка на организация'), 'billing': ('Billing', 'Плащания'), 'usage': ('Usage', 'Използване'),
 'defaultLanguage': ('Default organization language', 'Основен език на организацията'), 'notConfigured': ('Not configured', 'Не е настроено'),
 'invoiceDate': ('Invoice date', 'Дата на фактурата'), 'reservedQuantity': ('Reserved allowance', 'Заделено количество'),
 'reservationNotice': ('Uncertain deliveries keep allowance reserved until a verified provider status resolves the send.', 'При неясна доставка количеството остава заделено до проверено потвърждение от доставчика.'),
 'operations': ('Operations', 'Оперативен преглед'), 'administration': ('Platform administration', 'Администриране на платформата'),
 'saasMockNotice': ('SaaS foundation: payment and verification demonstrations are mocked. No real charge is made. Live providers and production operation require separate verification.', 'SaaS основа: плащанията и потвържденията в демонстрацията са симулирани. Няма реално таксуване. Реалните доставчици и продукционната работа изискват отделна проверка.'),
 'switchTenant': ('Switch organization', 'Смяна на организация'), 'registerOrganization': ('Register organization', 'Регистрация на организация'),
 'organizationName': ('Organization name', 'Име на организацията'), 'administratorEmail': ('Administrator email', 'Имейл на администратора'),
 'subscriptionPlan': ('Subscription plan', 'Абонаментен план'), 'onboardingStatus': ('Onboarding status', 'Състояние на регистрацията'),
 'readMockVerification': ('Read local mock verification', 'Преглед на локалното тестово потвърждение'),
 'verificationCode': ('Verification code', 'Код за потвърждение'), 'verifyEmail': ('Verify email', 'Потвърждение на имейла'),
 'emailVerified': ('Administrator email verified.', 'Имейлът на администратора е потвърден.'), 'startTrial': ('Start configured trial', 'Начало на настроения пробен период'),
 'adminOnly': ('Organization administrator access is required.', 'Необходим е достъп на администратор на организацията.'),
 'subscriptionStatus': ('Subscription status', 'Състояние на абонамента'), 'periodEnd': ('Period end', 'Край на периода'), 'gracePeriod': ('Grace period ends', 'Край на гратисния период'),
 'billingInterval': ('Billing interval', 'Период на плащане'), 'monthly': ('Monthly', 'Месечно'), 'annual': ('Annual', 'Годишно'),
 'prepareCheckout': ('Prepare mock checkout', 'Подготовка на тестово плащане'), 'changePlan': ('Change plan', 'Смяна на план'),
 'cancelSubscription': ('Cancel at period end', 'Прекратяване в края на периода'),
 'planChangePolicy': ('Upgrades require a confirmed checkout for a full new period. Downgrades apply at renewal. No automatic proration, tax or real payment is performed.', 'Надстройките изискват потвърдено плащане за нов пълен период. Понижаването се прилага при подновяване. Няма автоматично пропорционално таксуване, данъци или реални плащания.'),
 'invoices': ('Invoices · mock records', 'Фактури · тестови записи'), 'amount': ('Amount', 'Сума'), 'simulatePayment': ('Confirm mock payment', 'Потвърждение на тестово плащане'),
 'billingNotifications': ('Subscription notices', 'Известия за абонамента'), 'billingPeriod': ('Usage month · UTC', 'Месец на използване · UTC'),
 'tokenUsageNotice': ('Mock LLM token usage is unreported. Displayed totals cover recorded usage only; mock events do not create real charges.', 'Използването на токени от тестовия модел не се отчита. Сумите показват само записаното използване; тестовите събития не водят до реални такси.'),
 'usageCategory': ('Usage category', 'Категория на използване'), 'quantity': ('Quantity', 'Количество'), 'planLimit': ('Plan limit', 'Лимит на плана'), 'policy': ('Policy', 'Правило'),
 'workerHealth': ('Worker health', 'Състояние на обработчика'), 'operation': ('Operation', 'Операция'), 'errors': ('Errors', 'Грешки'), 'latencyMs': ('Mean latency · ms', 'Средна продължителност · ms'),
 'failedJobs': ('Failed or uncertain jobs', 'Неуспешни или неясни задачи'), 'credentialManagement': ('Credential management', 'Управление на данни за достъп'),
 'credentialName': ('Credential reference', 'Идентификатор на данните за достъп'), 'credentialValue': ('New secret value', 'Нова тайна стойност'),
 'rotateCredential': ('Store or rotate credential', 'Записване или подмяна на данните за достъп'), 'revoke': ('Revoke', 'Отмяна на достъпа'),
 'exportTenant': ('Export organization data', 'Експорт на данните на организацията'), 'tenantOverview': ('Tenant overview', 'Преглед на организациите'),
 'supportScopeNotice': ('Platform access requires a separate allowlist. Customer conversations require a tenant-approved, expiring support grant and audited access.', 'Достъпът до платформата изисква отделен списък с разрешения. Разговорите на клиентите изискват изрично разрешение от организацията със срок и одит на достъпа.'),
 'pending_verification': ('Pending email verification', 'Изчаква потвърждение на имейла'), 'configuring': ('Configuring', 'Настройване'), 'created': ('Created', 'Създаден'),
 'suspended': ('Suspended', 'Спрян'), 'trialing': ('Trial', 'Пробен период'), 'past_due': ('Payment overdue', 'Просрочено плащане'),
 'paid': ('Paid · mock provider', 'Платено · тестов доставчик'), 'failed': ('Failed', 'Неуспешно'), 'hard': ('Hard limit', 'Твърд лимит'), 'soft': ('Soft limit', 'Мек лимит'),
 'running': ('Running', 'Работи'), 'draining': ('Draining', 'Завършва текущите задачи'), 'stopped': ('Stopped', 'Спрян'), 'revoked': ('Revoked', 'Отнет'), 'legacy': ('Development fixture', 'Тестова среда'),
 'assistants': ('Assistants', 'Асистенти'), 'agents': ('Agents', 'Агенти'), 'users': ('Users', 'Потребители'), 'connections': ('Channel connections', 'Връзки на канали'),
 'ai_messages': ('AI messages', 'AI съобщения'), 'agent_executions': ('Agent executions', 'Изпълнения на агенти'), 'tool_executions': ('Tool executions', 'Изпълнения на инструменти'),
 'voice_seconds': ('Voice seconds', 'Гласови секунди'), 'stt_seconds': ('Recognition seconds', 'Секунди за разпознаване на говор'), 'tts_characters': ('Synthesis characters', 'Знаци за синтез на говор'),
 'sms_segments': ('SMS segments', 'SMS сегменти'), 'whatsapp_messages': ('WhatsApp messages', 'WhatsApp съобщения'), 'email_messages': ('Email messages', 'Имейл съобщения'),
 'llm_input_tokens': ('LLM input tokens', 'Входящи LLM токени'), 'llm_output_tokens': ('LLM output tokens', 'Изходящи LLM токени'), 'storage_bytes': ('Encrypted storage bytes', 'Байтове криптирано съхранение'),
 'api_request': ('API requests', 'API заявки'), 'agent_execution': ('Agent execution', 'Изпълнение на агент'), 'tool_execution': ('Tool execution', 'Изпълнение на инструмент'),
 'voice_turn': ('Voice turn', 'Гласова реплика'), 'channel_delivery': ('Channel delivery', 'Доставка по канал'), 'billing_webhook': ('Billing webhook', 'Уебхук за плащания'), 'background_job': ('Background jobs', 'Фонови задачи'),
 'worker_failed': ('Worker failed', 'Неуспешен обработчик'), 'inbound_message': ('Inbound message', 'Входящо съобщение'), 'outbound_message': ('Outbound message', 'Изходящо съобщение'),
 'scheduled_notification': ('Scheduled notification', 'Планирано известие'), 'appointment_reminder': ('Appointment reminder', 'Напомняне за час'), 'delivery_unknown': ('Delivery requires reconciliation', 'Доставката изисква проверка'),
}
from semantic_os.backend.assistant.language import TEXT
for index, locale in enumerate(('en-US', 'bg-BG')):
    path = ROOT / f'semantic_os/frontend/src/locales/{locale}.json'
    resources = json.loads(path.read_text(encoding='utf-8'))
    resources.update({key: pair[index] for key, pair in PAIRS.items()})
    for key in ('upgrade_required', 'verification_required', 'subscription_required', 'tenant_cancelled', 'usage_warning', 'payment_failed'):
        resources[key] = TEXT[locale][key]
    path.write_text(json.dumps(resources, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
