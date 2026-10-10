"""Bilingual resolution, templates and explicit tenant-timezone formatting."""
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from zoneinfo import ZoneInfo
from .domain import Locale, LOCALES, DomainError

TEXT = {
    'en-US': {
        'booking_confirmation_unclear':'I could not clearly understand your confirmation. Please confirm the proposed details or say cancel.',
        'voice_booking_confirm':'Please confirm: {name}, {date}, {duration} minutes. Say: yes, I confirm.',
        'invalid_model_output': 'The model returned an invalid response. No booking was confirmed.',
        'generation_cancelled': 'The interrupted response was stopped.',
        'invalid_model_checksum': 'The configured model files failed verification.',
        'invalid_model_manifest': 'The configured model manifest is invalid.',
        'model_license_required': 'The model license review is incomplete.',
        'inference_hardware_required': 'A compatible inference host must be configured.',
        'context_limit': 'The conversation exceeds the model context limit.',
        'hello': 'Hello! I can help with information, appointments and follow-up tasks.',
        'approval_required': 'Please confirm the requested action before I execute it.',
        'completed': 'The action was completed.', 'available': 'This time is available.',
        'unavailable': 'This time is unavailable.', 'escalated': 'A human follow-up was requested.',
        'appointment_created': 'Appointment confirmed for {date}.',
        'appointment_rescheduled': 'Appointment rescheduled for {date}.',
        'appointment_cancelled': 'The appointment was cancelled.',
        'reminder': 'Reminder: your appointment is on {date}.', 'subject': 'Appointment confirmation',
        'signature': 'Your assistant', 'opted_out': 'You have opted out of SMS messages.',
        'forbidden': 'You do not have permission for this action.', 'not_found': 'The item was not found.',
        'unauthorized': 'Sign in to continue.', 'invalid_input': 'Check the request and try again.',
        'conflict': 'The request conflicts with an existing item.', 'unsupported_locale': 'The provider does not support this language.',
        'unconfigured': 'This provider is not configured.', 'rate_limited': 'Too many requests. Try again shortly.',
        'budget_exceeded': 'The execution limit was reached.', 'disabled': 'This assistant or channel is disabled.',
        'invalid_signature': 'Webhook verification failed.', 'invalid_timezone': 'Choose a valid time zone.',
        'timezone_required': 'Include a time zone offset in the date.', 'tool_denied': 'This tool is not permitted.',
        'expired': 'This approval has expired.', 'limit_reached': 'The tenant usage limit was reached.',
        'invalid_transition': 'This call action is not available in the current state.',
        'provider_error': 'The provider could not complete this action.', 'timeout': 'The action timed out.',
        'appointment_details': 'Please provide the date, duration and contact name for the appointment request.',
        'cancel_details': 'Which appointment would you like to cancel?',
        'reschedule_details': 'Please select the appointment and provide its new date and duration.',
        'human_details': 'Please describe what you need help with so I can prepare a human follow-up request.',
        'booking_date': 'Please provide the appointment date and time, for example tomorrow at 15:00.',
        'booking_day': 'There are available times on the day of {date}. What exact time would you prefer? I will check that time before booking.',
        'booking_future': 'Please choose a future appointment date and time.',
        'booking_name': 'The time {date} is available for {duration} minutes. What is your name?',
        'booking_confirm': 'Please confirm: {name}, {date}, {duration} minutes. Reply "yes, confirm" or use Confirm action. No appointment has been booked yet.',
        'booking_unavailable': 'That time is unavailable. Please choose another date and time.',
        'booking_alternatives': 'Available alternatives: {slots}.',
        'booking_cancelled': 'The booking request was cancelled. No appointment was created.',
        'voice_language_switched': 'The call language has been changed to English.',
        'voice_human_request': 'The caller requested human assistance.',
        'unsupported_audio': 'This provider does not support the supplied audio format.',
        'voice_transfer_cancelled': 'The human transfer request was cancelled.',
        'attachment_received': 'Attachment received. Files are quarantined pending review.',
        'follow_up': 'Follow-up: {title}. {date}',
        'human_escalation': 'A human will review your request.',
        'consent_required': 'Messaging consent is required.',
        'template_required': 'An approved message template and consent are required.',
        'unsupported_attachment': 'This attachment format is not supported.',
        'upgrade_required': 'Your plan limit was reached. Upgrade or reduce usage to continue.',
        'verification_required': 'Verify the administrator email to continue.',
        'subscription_required': 'Activate or renew your subscription to continue.',
        'tenant_cancelled': 'This organization has been cancelled.',
        'verification_sent': 'Email verification is pending. Use the verified identity provider or the local mock verification message.',
        'billing_subject': 'Subscription update',
        'subscription_active': 'Your subscription is active.',
        'payment_failed': 'Payment failed. Review your subscription and grace period.',
        'usage_warning': 'Your usage is approaching the plan limit.',
    },
    'bg-BG': {
        'booking_confirmation_unclear':'Не разбрах ясно потвърждението. Моля, потвърдете предложените данни или кажете отказ.',
        'voice_booking_confirm':'Моля, потвърдете: {name}, {date}, {duration} минути. Кажете: да, потвърждавам.',
        'invalid_model_output': 'Моделът върна невалиден отговор. Не е потвърден час.',
        'generation_cancelled': 'Прекъснатият отговор е спрян.',
        'invalid_model_checksum': 'Настроените файлове на модела не преминаха проверката.',
        'invalid_model_manifest': 'Настроеният манифест на модела е невалиден.',
        'model_license_required': 'Проверката на лиценза на модела не е завършена.',
        'inference_hardware_required': 'Необходимо е да се настрои съвместим сървър за модела.',
        'context_limit': 'Разговорът надвишава контекстния лимит на модела.',
        'hello': 'Здравейте! Мога да помогна с информация, часове и последващи задачи.',
        'approval_required': 'Моля, потвърдете заявеното действие, преди да го изпълня.',
        'completed': 'Действието е изпълнено.', 'available': 'Този час е свободен.',
        'unavailable': 'Този час е зает.', 'escalated': 'Заявена е последваща връзка с човек.',
        'appointment_created': 'Часът е потвърден за {date}.',
        'appointment_rescheduled': 'Часът е преместен за {date}.',
        'appointment_cancelled': 'Часът е отменен.',
        'reminder': 'Напомняне: Вашият час е на {date}.', 'subject': 'Потвърждение на час',
        'signature': 'Вашият асистент', 'opted_out': 'Отказахте получаването на SMS съобщения.',
        'forbidden': 'Нямате разрешение за това действие.', 'not_found': 'Елементът не е намерен.',
        'unauthorized': 'Влезте в профила си, за да продължите.', 'invalid_input': 'Проверете заявката и опитайте отново.',
        'conflict': 'Заявката е в конфликт със съществуващ елемент.', 'unsupported_locale': 'Доставчикът не поддържа този език.',
        'unconfigured': 'Този доставчик не е конфигуриран.', 'rate_limited': 'Твърде много заявки. Опитайте отново скоро.',
        'budget_exceeded': 'Достигнат е лимитът за изпълнение.', 'disabled': 'Този асистент или канал е изключен.',
        'invalid_signature': 'Проверката на уебхука е неуспешна.', 'invalid_timezone': 'Изберете валидна часова зона.',
        'timezone_required': 'Добавете отместване на часовата зона в датата.', 'tool_denied': 'Този инструмент не е разрешен.',
        'expired': 'Това потвърждение е изтекло.', 'limit_reached': 'Достигнат е лимитът за използване на организацията.',
        'invalid_transition': 'Това действие не е достъпно в текущото състояние на разговора.',
        'provider_error': 'Доставчикът не успя да изпълни действието.', 'timeout': 'Времето за изпълнение изтече.',
        'appointment_details': 'Моля, посочете дата, продължителност и име на контакта за заявката за час.',
        'cancel_details': 'Кой час искате да отмените?',
        'reschedule_details': 'Моля, изберете часа и посочете новата дата и продължителност.',
        'human_details': 'Моля, опишете с какво Ви трябва помощ, за да подготвя заявка за връзка с човек.',
        'booking_date': 'Моля, посочете дата и час, например утре в 15:00.',
        'booking_day': 'Има свободни часове в деня на {date}. Кой точен час предпочитате? Ще проверя този час преди записване.',
        'booking_future': 'Моля, изберете бъдеща дата и час.',
        'booking_name': 'Часът {date} е свободен за {duration} минути. Как се казвате?',
        'booking_confirm': 'Моля, потвърдете: {name}, {date}, {duration} минути. Отговорете „да, потвърждавам“ или използвайте бутона за потвърждение. Все още няма записан час.',
        'booking_unavailable': 'Този час е зает. Моля, изберете друга дата и час.',
        'booking_alternatives': 'Свободни варианти: {slots}.',
        'booking_cancelled': 'Заявката за записване е отменена. Не е създаден час.',
        'voice_language_switched': 'Езикът на обаждането е променен на български.',
        'voice_human_request': 'Обаждащият се поиска помощ от човек.',
        'unsupported_audio': 'Доставчикът не поддържа този аудиоформат.',
        'voice_transfer_cancelled': 'Заявката за връзка с човек е отменена.',
        'attachment_received': 'Файлът е получен и е под карантина до преглед.',
        'follow_up': 'Последваща задача: {title}. {date}',
        'human_escalation': 'Човек ще прегледа Вашата заявка.',
        'consent_required': 'Необходимо е съгласие за съобщения.',
        'template_required': 'Необходими са одобрен шаблон и съгласие.',
        'unsupported_attachment': 'Този файлов формат не се поддържа.',
        'upgrade_required': 'Достигнат е лимитът на плана. Надстройте плана или намалете използването.',
        'verification_required': 'Потвърдете имейла на администратора, за да продължите.',
        'subscription_required': 'Активирайте или подновете абонамента, за да продължите.',
        'tenant_cancelled': 'Тази организация е закрита.',
        'verification_sent': 'Изчаква се потвърждение на имейла. Използвайте доставчика на удостоверяване или локалното тестово съобщение.',
        'billing_subject': 'Промяна в абонамента',
        'subscription_active': 'Вашият абонамент е активен.',
        'payment_failed': 'Плащането е неуспешно. Проверете абонамента и гратисния период.',
        'usage_warning': 'Използването Ви наближава лимита на плана.',
    },
}


def tr(locale: Locale, key: str, **values) -> str:
    return TEXT[locale].get(key, TEXT[locale]['invalid_input']).format(**values)


@dataclass(frozen=True)
class Resolution:
    locale: Locale
    source: str
    confidence: float
    uncertain: bool


class LanguageResolver:
    def detect(self, content: str) -> tuple[Locale | None, float]:
        words = set(re.findall(r'[a-zа-я]+', content.lower()))
        bg = words & {'здравейте', 'здравей', 'час', 'искам', 'благодаря', 'записване', 'отмяна', 'запиша', 'запиши', 'утре', 'днес', 'потвърждавам'}
        en = words & {'hello', 'appointment', 'please', 'thanks', 'reschedule', 'cancel', 'book', 'booking', 'tomorrow', 'today', 'confirm'}
        if bg and not en:
            return 'bg-BG', 0.95
        if en and not bg:
            return 'en-US', 0.95
        return None, 0.0

    def resolve(self, content: str, *, explicit=None, contact=None, conversation=None,
                assistant=None, tenant=None, platform: Locale = 'en-US') -> Resolution:
        detected, confidence = self.detect(content)
        explicit = explicit or {'please continue in english': 'en-US', 'please continue in bulgarian': 'bg-BG',
            'switch to english': 'en-US', 'премини на английски': 'en-US',
            'switch to bulgarian': 'bg-BG', 'премини на български': 'bg-BG'}.get(content.casefold().strip(' .!'))
        candidates = [('explicit', explicit), ('contact', contact), ('conversation', conversation),
                      ('detection', detected if confidence >= .9 else None), ('assistant', assistant),
                      ('tenant', tenant), ('platform', platform)]
        for source, locale in candidates:
            if locale is not None:
                if locale not in LOCALES:
                    raise DomainError('unsupported_locale')
                return Resolution(locale, source, confidence, detected is None)
        raise DomainError('unsupported_locale')


def format_date(value: str | datetime, locale: Locale, timezone: str) -> str:
    date = datetime.fromisoformat(value) if isinstance(value, str) else value
    if date.tzinfo is None:
        raise DomainError('timezone_required')
    date = date.astimezone(ZoneInfo(timezone))
    return date.strftime('%d.%m.%Y %H:%M' if locale == 'bg-BG' else '%m/%d/%Y %I:%M %p') + ' ' + timezone


def parse_date(value: str, locale: Locale, timezone: str, reference: datetime | None = None) -> datetime:
    """ISO/numeric dates and a small explicit bilingual weekday vocabulary."""
    reference = reference or datetime.now(ZoneInfo(timezone))
    reference = reference.astimezone(ZoneInfo(timezone))
    vocab = {'bg-BG': ['понеделник', 'вторник', 'сряда', 'четвъртък', 'петък', 'събота', 'неделя'],
             'en-US': ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']}
    # Temporal words can be understood independently of the response/UI locale.
    relative = {'днес': 0, 'утре': 1, 'today': 0, 'tomorrow': 1}
    weekdays = {word: index for names in vocab.values() for index, word in enumerate(names)}
    match = re.fullmatch(r'(?:(next|следващия)\s+)?([a-zа-я]+)\s+(?:(?:at|в)\s+)?(\d{1,2})(?::(\d{2}))?\s*(am|pm)?', value.strip().casefold())
    if match:
        next_word, word, hour, minute, meridian = match.groups()
        minute = minute or '00'
        if meridian:
            if not 1 <= int(hour) <= 12: raise DomainError('invalid_input', 422)
            hour = str(int(hour)%12 + (12 if meridian == 'pm' else 0))
        if int(hour) > 23 or int(minute) > 59:
            raise DomainError('invalid_input', 422)
        if word in relative:
            delta = relative[word]
        elif word in weekdays:
            delta = (weekdays[word] - reference.weekday()) % 7
            if delta == 0 and (next_word or (int(hour), int(minute)) <= (reference.hour, reference.minute)):
                delta = 7
        else:
            raise DomainError('invalid_input', 422)
        target = reference.date() + timedelta(days=delta)
        value = f'{target.isoformat()}T{int(hour):02d}:{minute}'
    try:
        date = datetime.fromisoformat(value)
    except ValueError:
        try:
            date = datetime.strptime(value, '%d.%m.%Y %H:%M' if locale == 'bg-BG' else '%m/%d/%Y %I:%M %p')
        except ValueError:
            raise DomainError('invalid_input') from None
    if date.tzinfo is not None:
        return date
    zone = ZoneInfo(timezone)
    # Reject ambiguous and nonexistent DST wall-clock times; request an explicit offset.
    first, second = date.replace(tzinfo=zone, fold=0), date.replace(tzinfo=zone, fold=1)
    if first.utcoffset() != second.utcoffset():
        raise DomainError('timezone_required')
    return first


def parse_duration(value: str, locale: Locale) -> int:
    units = {'bg-BG': {'час': 60, 'часа': 60, 'часове': 60, 'минута': 1, 'минути': 1, 'мин': 1},
             'en-US': {'hour': 60, 'hours': 60, 'minute': 1, 'minutes': 1, 'min': 1}}[locale]
    parts = re.findall(r'(\d+)\s*([a-zа-я]+)', value.strip().casefold())
    remainder = re.sub(r'\d+\s*[a-zа-я]+', '', value.strip().casefold()).strip()
    if not parts or remainder or any(unit not in units for _, unit in parts):
        raise DomainError('invalid_input', 422)
    minutes = sum(int(amount) * units[unit] for amount, unit in parts)
    if not 5 <= minutes <= 480:
        raise DomainError('invalid_input', 422)
    return minutes
