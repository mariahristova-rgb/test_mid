"""Live delivery infrastructure. Ambiguous sends are never automatically retried."""
import base64
from email.message import EmailMessage
import json
import os
import re
import smtplib
import ssl
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from .domain import DomainError
from .providers import safe_email_html


class DeliveryFailure(DomainError):
    def __init__(self, code='provider_error', *, retry_safe=False, uncertain=False):
        self.retry_safe, self.uncertain = retry_safe, uncertain
        super().__init__(code, 502)


def gated(connection):
    if not connection.get('enable_live') or os.getenv('ASSISTANT_ENABLE_LIVE_MESSAGING', '') != 'true':
        raise DomainError('unconfigured', 503)


def post(url, data, headers):
    try:
        with urlopen(Request(url, data=data, headers=headers, method='POST'), timeout=8) as response:
            result = response.read(1_000_001)
            if len(result) > 1_000_000: raise DeliveryFailure(uncertain=True)
            return json.loads(result)
    except HTTPError as error:
        # Explicit rate-limit rejection is retryable; 5xx/timeouts may have
        # accepted the message and therefore require reconciliation instead.
        raise DeliveryFailure('rate_limited' if error.code == 429 else 'provider_error',
                              retry_safe=error.code == 429, uncertain=error.code >= 500) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise DeliveryFailure(uncertain=True) from None


def send_meta(message, connection, credentials, key):
    gated(connection)
    if not re.fullmatch(r'v\d+\.\d+', connection['api_version']) or not connection['phone_number_id'].isdigit():
        raise DomainError('invalid_input', 422)
    payload = {'messaging_product': 'whatsapp', 'to': message['recipient'].lstrip('+'),
               'biz_opaque_callback_data': message['id']}
    template = message['metadata'].get('provider_template')
    if template:
        payload.update(type='template', template={'name': template['name'], 'language': {'code': template['language']},
            'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': str(value)} for value in template.get('parameters', [])]}]})
    else:
        payload.update(type='text', text={'body': message['content']})
    result = post(f"https://graph.facebook.com/{connection['api_version']}/{connection['phone_number_id']}/messages",
                  json.dumps(payload, ensure_ascii=False).encode(), {'Authorization': 'Bearer ' + credentials['access_token'], 'Content-Type': 'application/json'})
    try: id = result['messages'][0]['id']
    except (KeyError, IndexError, TypeError): raise DeliveryFailure(uncertain=True) from None
    return {'external_message_id': id, 'status': 'sent', 'state': 'LIVE_UNVERIFIED'}


def send_twilio_sms(message, connection, credentials, key):
    gated(connection)
    account = connection['account_sid']
    if not re.fullmatch(r'AC[0-9a-fA-F]{32}', account): raise DomainError('invalid_input', 422)
    callback = connection['public_origin'].rstrip('/') + '/webhooks/messaging/' + connection['tenant_id'] + '/' + connection['id'] + '/status/' + message['id']
    body = urlencode({'From': connection['sender_id'], 'To': message['recipient'], 'Body': message['content'], 'StatusCallback': callback}).encode()
    credential = base64.b64encode((account + ':' + credentials['auth_token']).encode()).decode()
    result = post(f'https://api.twilio.com/2010-04-01/Accounts/{account}/Messages.json', body,
                  {'Authorization': 'Basic ' + credential, 'Content-Type': 'application/x-www-form-urlencoded'})
    if not result.get('sid'): raise DeliveryFailure(uncertain=True)
    return {'external_message_id': result['sid'], 'status': 'sent', 'state': 'LIVE_UNVERIFIED'}


class SMTPEmailProvider:
    def send_message(self, message, connection, credentials, key):
        gated(connection)
        host = connection['smtp_host']
        if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9.-]{2,200}', host) or host.replace('.', '').isdigit() or host in ('localhost',):
            raise DomainError('invalid_input', 422)
        email = EmailMessage()
        email['From'], email['To'] = connection['sender_id'], message['recipient']
        subject = message['metadata'].get('subject', '')
        if '\r' in subject or '\n' in subject: raise DomainError('invalid_input', 422)
        email['Subject'] = subject
        email['Message-ID'] = '<' + message['id'] + '@' + connection['sender_id'].split('@')[1] + '>'
        parent = message['metadata'].get('in_reply_to')
        if parent and not any(c in parent for c in '\r\n'): email['In-Reply-To'] = parent
        email.set_content(message['content'])
        email.add_alternative(safe_email_html(message['content']), subtype='html')
        try:
            if connection['smtp_port'] == 465:
                smtp = smtplib.SMTP_SSL(host, 465, timeout=8, context=ssl.create_default_context())
            else:
                smtp = smtplib.SMTP(host, 587, timeout=8)
                smtp.starttls(context=ssl.create_default_context())
            with smtp:
                smtp.login(connection['smtp_username'], credentials['smtp_password'])
                smtp.send_message(email)
        except (OSError, smtplib.SMTPException):
            raise DeliveryFailure(uncertain=True) from None
        return {'external_message_id': email['Message-ID'], 'status': 'sent', 'state': 'LIVE_UNVERIFIED'}
