#!/bin/sh
set -eu
cd /opt/testmid-phase15
# The fixed package contains only reviewed config/public FAQ; no customer data.
docker load -i /tmp/staging-images.tar
tar -xf /tmp/staging-config.tar -C /opt/testmid-phase15
install -d -m 0700 -o 10001 -g 10001 data secrets
install -d -m 0755 -o 10001 -g 10001 site
python3 - <<'PY'
import base64,os,secrets
from pathlib import Path
path=Path('/opt/testmid-phase15/secrets/tenant-key')
if not path.exists():
    with path.open('x') as output:output.write(base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())
os.chown(path,10001,10001);os.chmod(path,0o400)
PY
docker-compose -p testmid-phase15-staging -f compose.yml config --quiet
docker-compose -p testmid-phase15-staging -f compose.yml run --rm --no-deps -e ASSISTANT_STAGING_BOOTSTRAP=true backend python /bootstrap.py prepare
docker-compose -p testmid-phase15-staging -f compose.yml up -d
docker-compose -p testmid-phase15-staging -f compose.yml ps
