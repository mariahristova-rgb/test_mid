"""Bounded MIME parsing for signed inbound email connectors."""
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
import base64
import re
from .domain import DomainError


class PlainHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = 0
        self.parts = []
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'iframe', 'object', 'template'): self.hidden += 1
        if tag in ('p', 'br', 'div', 'li') and not self.hidden: self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'iframe', 'object', 'template') and self.hidden: self.hidden -= 1
    def handle_data(self, text):
        if not self.hidden: self.parts.append(text)


def html_to_text(value):
    parser = PlainHTML()
    parser.feed(value)
    return ''.join(parser.parts).strip()


def parse_mime(raw: bytes) -> dict:
    if len(raw) > 10_000_000:
        raise DomainError('invalid_input', 413)
    mail = BytesParser(policy=policy.default).parsebytes(raw)
    body, html, attachments = [], [], []
    for part in mail.walk():
        if part.is_multipart():
            continue
        payload = part.get_payload(decode=True) or b''
        if part.get_content_disposition() == 'attachment' or part.get_filename():
            attachments.append({'name': (part.get_filename() or 'attachment')[:200],
                                'media_type': part.get_content_type(), 'size': len(payload), 'data_base64': base64.b64encode(payload).decode()})
        elif part.get_content_type() == 'text/plain':
            try:
                body.append(payload.decode(part.get_content_charset() or 'utf-8', errors='replace'))
            except LookupError:
                raise DomainError('invalid_input', 422) from None
        elif part.get_content_type() == 'text/html':
            try: html.append(payload.decode(part.get_content_charset() or 'utf-8', errors='replace'))
            except LookupError: raise DomainError('invalid_input', 422) from None
    content = '\n'.join(body) if body else html_to_text('\n'.join(html))
    if len(content) > 10000 or len(attachments) > 10: raise DomainError('invalid_input', 422)
    return {'subject': str(mail.get('Subject', '')), 'sender': str(mail.get('From', '')),
            'recipient': str(mail.get('To', '')), 'message_id': str(mail.get('Message-ID', '')),
            'in_reply_to': str(mail.get('In-Reply-To', '')), 'references': re.findall(r'<[^>\r\n]+>', str(mail.get('References', ''))),
            'body': content, 'attachments': attachments, 'requires_plain_text': not bool(content)}
