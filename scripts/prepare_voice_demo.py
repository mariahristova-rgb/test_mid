"""Generate private Asterisk demo config from environment secret references; print no credentials."""
import os
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]


def prepare(directory):
    passwords = {key: os.getenv(key, '') for key in ('SIP_DEMO_PASSWORD','ARI_PASSWORD')}
    if any(not re.fullmatch(r'[A-Za-z0-9]{32,128}', value) for value in passwords.values()):
        raise ValueError('Set SIP_DEMO_PASSWORD and ARI_PASSWORD to separate 32+ character alphanumeric secrets')
    if passwords['SIP_DEMO_PASSWORD'] == passwords['ARI_PASSWORD']: raise ValueError('Separate credentials are required')
    directory = Path(directory).resolve()
    if not directory.is_relative_to(ROOT/'artifacts'): raise ValueError('Generated credential config must remain in ignored test_mid/artifacts')
    directory.mkdir(parents=True, exist_ok=True)
    values = {
        'pjsip.conf': '[transport-udp]\ntype=transport\nprotocol=udp\nbind=0.0.0.0:5060\nlocal_net=172.30.7.0/24\nexternal_media_address=127.0.0.1\nexternal_signaling_address=127.0.0.1\n\n[1001]\ntype=endpoint\ncontext=testmid-demo\ntransport=transport-udp\nmedia_address=127.0.0.1\nbind_rtp_to_media_address=no\ndisallow=all\nallow=ulaw\nauth=1001-auth\naors=1001\ndirect_media=no\nrtp_symmetric=yes\nforce_rport=yes\nrewrite_contact=yes\n\n[1001-auth]\ntype=auth\nauth_type=userpass\nusername=1001\npassword='+passwords['SIP_DEMO_PASSWORD']+'\n\n[1001]\ntype=aor\nmax_contacts=1\nremove_existing=yes\n',
        'extensions.conf':'[testmid-demo]\nexten => 2000,1,NoOp(TestMid private demo)\n same => n,Stasis(testmid-voice)\n same => n,Hangup()\n',
        'ari.conf':'[general]\nenabled=yes\npretty=no\n[testmid-voice]\ntype=user\nread_only=no\npassword='+passwords['ARI_PASSWORD']+'\n',
        'http.conf':'[general]\nenabled=yes\nbindaddr=0.0.0.0\nbindport=8088\n',
        'rtp.conf':'[general]\nrtpstart=10000\nrtpend=10099\nstrictrtp=yes\n'}
    for name, value in values.items():
        if (directory/name).exists(): raise ValueError('Refusing to overwrite existing config; inspect/rotate explicitly')
    for name, value in values.items():
        target = directory/name
        target.write_text(value, encoding='utf-8')
        target.chmod(0o600)
    return directory


if __name__ == '__main__':
    prepare(ROOT/'artifacts/voice-demo/asterisk')
    print('Private Asterisk configuration prepared in artifacts/voice-demo/asterisk; credentials are not printed.')
