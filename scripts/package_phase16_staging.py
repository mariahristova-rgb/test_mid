"""Create a credential-free isolated staging package; never include local data/models."""
import hashlib
import json
from pathlib import Path
import tarfile
import io

ROOT=Path(__file__).resolve().parents[1]
FILES=('compose.yml','bootstrap.py','nginx.conf','Caddyfile')

def main():
    destination=ROOT/'artifacts/phase16/staging-config.tar'
    hashes={}
    with tarfile.open(destination,'w') as archive:
        for name in FILES:
            content=(ROOT/'semantic_os/deploy/phase15-staging'/name).read_text(encoding='utf-8-sig').replace('\r\n','\n').encode()
            item=tarfile.TarInfo(name);item.size=len(content);item.mode=0o644
            archive.addfile(item,io.BytesIO(content));hashes[name]=hashlib.sha256(content).hexdigest()
        approved=json.loads((ROOT/'semantic_os/config/ontelyx_concierge.json').read_text(encoding='utf-8'))
        content=json.dumps({'faq_entries':approved['faq_entries']},ensure_ascii=False).encode()
        item=tarfile.TarInfo('approved-public-config.json');item.size=len(content);item.mode=0o644
        archive.addfile(item,io.BytesIO(content));hashes[item.name]=hashlib.sha256(content).hexdigest()
    (ROOT/'artifacts/phase16/staging-package-hashes.json').write_text(json.dumps(hashes,indent=2))
    print('Packaged five reviewed configuration files and approved FAQ content; no credentials or databases.')

if __name__=='__main__':main()
