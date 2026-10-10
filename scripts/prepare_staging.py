"""Generate isolated local staging fixture material in the ignored workspace artifacts directory."""
from datetime import datetime, timedelta, timezone
import ipaddress
import json
from pathlib import Path
import os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.fernet import Fernet
import jwt

ROOT = Path(__file__).resolve().parents[1]
directory = ROOT / 'artifacts/staging'
directory.mkdir(parents=True, exist_ok=True)
private = directory / 'signing.key'
if not private.exists():
    signing = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private.write_bytes(signing.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    private.chmod(0o600)
else: signing = serialization.load_pem_private_key(private.read_bytes(), password=None)
(directory / 'staging-public.pem').write_bytes(signing.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))
at = datetime.now(timezone.utc)
if not (directory / 'staging.crt').exists():
    tls_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    cert = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(tls_key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(at - timedelta(minutes=1)).not_valid_after(at + timedelta(days=2)).add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost'), x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]), critical=False).sign(tls_key, hashes.SHA256())
    (directory / 'staging.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    (directory / 'staging.key').write_bytes(tls_key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (directory / 'staging.key').chmod(0o600)
environment = directory / 'staging.env'
if not environment.exists():
    environment.write_text('ASSISTANT_ENCRYPTION_KEY=' + Fernet.generate_key().decode() + '\nASSISTANT_BACKUP_ENCRYPTION_KEY=' + Fernet.generate_key().decode() + '\nSTAGING_ARTIFACT_DIRECTORY=' + directory.as_posix() + '\n', encoding='utf-8')
    environment.chmod(0o600)
token = jwt.encode({'sub': 'staging-owner', 'email': 'owner@example.invalid', 'email_verified': True,
    'iss': 'https://identity.staging.example.invalid/', 'aud': 'staging-api', 'iat': at, 'exp': at + timedelta(hours=1)}, signing, algorithm='RS256')
(directory / 'session.json').write_text(json.dumps({'token': token, 'tenant_id': 'staging', 'origin': 'https://127.0.0.1:8443'}), encoding='utf-8')
(directory / 'session.json').chmod(0o600)
print('Isolated staging fixture material prepared in ignored artifacts/staging; no secrets printed.')
