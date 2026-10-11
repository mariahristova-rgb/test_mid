"""Owner-approved isolated host. Default is quote-only; never touches existing services."""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
PROJECT='strong-keel-468007-r7'
ZONE='us-central1-a'
NAME='testmid-phase15-staging'
CLI=r'C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd'

def command(*args):
    result=subprocess.run([CLI,*args,'--project='+PROJECT,'--quiet'],capture_output=True,text=True,timeout=180)
    if result.returncode:raise RuntimeError('gcloud action failed: '+args[0]+' '+args[1])
    return result.stdout.strip()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    rows=json.loads((ROOT/'artifacts/phase15/cloud-eur-sku-quote.json').read_text())
    prices={r['description']:r['price'] for r in rows if r['currency']=='EUR'}
    core=prices['E2 Instance Core running in Americas'];ram=prices['E2 Instance Ram running in Americas'];ip=prices['External IP Charge on a Standard VM'];disk=prices['Storage PD Capacity']
    # e2-micro: quarter sustained CPU and 1GiB RAM. No free-tier credit assumed.
    # Retain the reserved IP after STOP so owned DNS never points at a recycled IP.
    # One weekly run: 72h compute, 168h IP, 7/30 of a 10GiB standard disk.
    estimate=((core*.25+ram)*72+ip*168+disk*10*(7/30))*1.30+.20
    if estimate>2:raise RuntimeError('Conservative weekly cost estimate exceeds approved weekly ceiling')
    report={'project':PROJECT,'host':NAME,'machine':'e2-micro','region':'us-central1','max_run_hours':72,'disk_gib':10,'estimated_eur_with_30_percent_contingency_and_network_reserve':round(estimate,4),'budget_eur_per_week':2,'scope':'text-only-synthetic-staging','quote_source':'Google Cloud Billing catalog, EUR, 11 October 2026','free_tier_assumed':False}
    if not args.apply:print(json.dumps(report,indent=2));return
    previous=json.loads(command('compute','instances','list','--filter=name='+NAME,'--format=json'))
    if previous:raise RuntimeError('Host already exists; no replacement or extra instance is permitted')
    command('services','enable','iap.googleapis.com')
    account=NAME+'@'+PROJECT+'.iam.gserviceaccount.com'
    accounts=json.loads(command('iam','service-accounts','list','--filter=email='+account,'--format=json'))
    if not accounts:command('iam','service-accounts','create',NAME,'--display-name=Isolated Phase15 OAuth credential reader')
    for secret in ('G_CLIENT_ID','G_CLIENT_SECRET'):
        command('secrets','add-iam-policy-binding',secret,'--member=serviceAccount:'+account,'--role=roles/secretmanager.secretAccessor','--condition=None','--format=none')
    networks=json.loads(command('compute','networks','list','--filter=name='+NAME,'--format=json'))
    if not networks:command('compute','networks','create',NAME,'--subnet-mode=custom','--bgp-routing-mode=regional')
    subnets=json.loads(command('compute','networks','subnets','list','--filter=name='+NAME,'--format=json'))
    if not subnets:command('compute','networks','subnets','create',NAME,'--network='+NAME,'--region=us-central1','--range=10.151.15.0/28')
    for suffix,allowed,source in [('https','tcp:80,tcp:443','0.0.0.0/0'),('iap','tcp:22','35.235.240.0/20')]:
        rule=NAME+'-'+suffix
        exists=json.loads(command('compute','firewall-rules','list','--filter=name='+rule,'--format=json'))
        if not exists:command('compute','firewall-rules','create',rule,'--network='+NAME,'--allow='+allowed,'--source-ranges='+source,'--target-tags='+NAME)
    deadline=(datetime.now(timezone.utc)+timedelta(hours=72)).strftime('%Y-%m-%dT%H:%M:%SZ')
    command('compute','instances','create',NAME,'--zone='+ZONE,'--machine-type=e2-micro','--subnet='+NAME,'--tags='+NAME,
        '--image-family=debian-12','--image-project=debian-cloud','--boot-disk-type=pd-standard','--boot-disk-size=10GB','--no-boot-disk-auto-delete',
        '--service-account='+account,'--scopes=https://www.googleapis.com/auth/cloud-platform','--no-restart-on-failure','--maintenance-policy=TERMINATE','--instance-termination-action=STOP','--termination-time='+deadline,
        '--metadata=enable-oslogin=TRUE,block-project-ssh-keys=TRUE,serial-port-enable=FALSE','--labels=application=test-mid,phase=phase15,environment=staging',
        '--metadata-from-file=startup-script='+str(ROOT/'semantic_os/deploy/phase15-staging/startup.sh'))
    address=command('compute','instances','describe',NAME,'--zone='+ZONE,'--format=value(networkInterfaces[0].accessConfigs[0].natIP)')
    command('compute','addresses','create',NAME,'--region=us-central1','--addresses='+address)
    report.update(public_ipv4=address,automatic_stop_utc=deadline,https_state='DNS_AND_TLS_PENDING',staff_public_access=False)
    (ROOT/'artifacts/phase15/cloud-host-state.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Staging provisioning stopped: '+str(error))
        raise SystemExit(1) from None
