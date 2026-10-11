"""Actual bundle/HTTP measurements; deliberately no browser vitals claims."""
import gzip
import json
from pathlib import Path
import statistics
from time import perf_counter
import urllib.request
from phase13b_ontelyx_demo import ROOT,DIRECTORY,WEBSITE,STATE,SITE,WIDGET

def main():
    baseline=json.loads((DIRECTORY/'website-baseline-bundles.json').read_text())
    final={path.name:{'bytes':path.stat().st_size,'gzip_bytes':len(gzip.compress(path.read_bytes()))} for path in (WEBSITE/'dist/assets').iterdir() if path.is_file()}
    entry=lambda values:next(value for name,value in values.items() if name.startswith('index-') and name.endswith('.js'))
    state=json.loads(STATE.read_text());samples={}
    for name,url in {'homepage':SITE+'/','assistant_route':SITE+'/ai-assistant','loader':WIDGET+'/widget/assets/v1.js'}.items():
        times=[]
        for _ in range(20):
            start=perf_counter()
            with urllib.request.urlopen(url,timeout=10) as response:response.read()
            times.append((perf_counter()-start)*1000)
        samples[name]={'samples':20,'p50_ms':round(statistics.median(times),2),'p95_ms':round(sorted(times)[18],2)}
    result={'baseline_entry':entry(baseline),'final_entry':entry(final),'baseline_asset_bytes':sum(row['bytes'] for row in baseline.values()),'final_asset_bytes':sum(row['bytes'] for row in final.values()),'http':samples,'loader_bytes':(ROOT/'semantic_os/widget/v1.js').stat().st_size,'loader_gzip_bytes':len(gzip.compress((ROOT/'semantic_os/widget/v1.js').read_bytes())),'website_assets':final,'browser_vitals':'BLOCKED','message_latency_ms':state['message_latency_ms'],'method':'20 sequential Windows loopback urllib samples per GET, no rendering/throttling/mobile engine; before/after emitted bundle bytes only.'}
    (DIRECTORY/'performance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({key:value for key,value in result.items() if key!='website_assets'},indent=2))

if __name__=='__main__':main()
