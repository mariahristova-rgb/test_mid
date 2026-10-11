"""Read-only local concierge/clinic verification. Never calls live Google APIs."""
import gzip
import json
from pathlib import Path
from time import perf_counter
import statistics
import urllib.request
from phase12_local_journey import ROOT,BASE,WIDGET,request

def main():
    directory=ROOT/'artifacts/phase14';state=json.loads((directory/'demo-state.json').read_text())
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    headers={'Authorization':'Bearer '+login['access_token'],'X-Tenant-ID':state['tenant_id']}
    connections=request(BASE,'/api/google',headers);policy=request(BASE,'/api/concierge/policy',headers)
    bookings=request(BASE,'/api/appointments',headers)
    assert policy['calendar_id']=='primary'
    widget=next(row for row in request(BASE,'/api/widgets',headers) if row['id']==state['widget_id'])
    assert widget['state']=='published' and widget['settings']['concierge_enabled']
    latencies={}
    for name,url in {'website':'http://127.0.0.1:5173/ai-assistant/','loader':WIDGET+'/widget/assets/v1.js','admin':'http://127.0.0.1:3017/google'}.items():
        samples=[]
        for _ in range(20):
            start=perf_counter()
            with urllib.request.urlopen(url,timeout=10) as response:assert response.status==200;response.read()
            samples.append((perf_counter()-start)*1000)
        latencies[name]={'samples':20,'p50_ms':round(statistics.median(samples),2),'p95_ms':round(sorted(samples)[18],2)}
    source=ROOT/'artifacts/phase13b/ontelyx/dist/assets'
    entry=next(path for path in source.iterdir() if path.name.startswith('index-') and path.suffix=='.js')
    loader=ROOT/'semantic_os/widget/v1.js'
    report={'google_connections':sum(row['state']=='connected' for row in connections),'connection_states':[{'connection':row['connection'],'state':row['state']} for row in connections],'live_operations_authorized':policy['operations_authorized'],'real_bookings':len(bookings),'calendar':'primary','concierge_published':True,'http':latencies,
        'website_entry_bytes':entry.stat().st_size,'website_entry_gzip_bytes':len(gzip.compress(entry.read_bytes())),'loader_bytes':loader.stat().st_size,'loader_gzip_bytes':len(gzip.compress(loader.read_bytes())),
        'browser_mobile_vitals':'NOT_MEASURED','live_google_test':'NOT_RUN','method':'20 sequential local urllib HTTP GETs; no browser engine, mobile or throttling.'}
    (directory/'local-final-state.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
