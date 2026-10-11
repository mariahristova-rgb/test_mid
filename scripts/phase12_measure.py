"""Measure source bytes and actual localhost HTTP; never emulate browser vitals."""
import gzip
import json
from pathlib import Path
import statistics
from time import perf_counter
from urllib.parse import urlencode
import urllib.request

ROOT=Path(__file__).resolve().parents[1]

def main():
    state=json.loads((ROOT/'artifacts/phase12-journey-state.json').read_text())
    assets={}
    for path in (ROOT/'semantic_os/widget').iterdir():
        if path.is_file():
            content=path.read_bytes();assets[path.name]={'bytes':len(content),'gzip_bytes':len(gzip.compress(content))}
    samples={}
    for name,url in {
        'loader':'http://127.0.0.1:3020/widget/assets/v1.js',
        'iframe':'http://127.0.0.1:3020/widget/frame/'+state['public_id']+'?'+urlencode({'parent_origin':'http://127.0.0.1:3021'}),
        'sample_site':'http://127.0.0.1:3021/'}.items():
        latencies=[]
        for _ in range(20):
            start=perf_counter()
            with urllib.request.urlopen(url,timeout=10) as response:content=response.read()
            latencies.append((perf_counter()-start)*1000)
        ordered=sorted(latencies)
        samples[name]={'n':20,'p50_ms':round(statistics.median(latencies),2),'p95_ms':round(ordered[18],2),'response_bytes':len(content)}
    bundle=sum(path.stat().st_size for path in (ROOT/'semantic_os/frontend/dist').rglob('*') if path.is_file())
    result={'assets':assets,'http':samples,'dashboard_bundle_bytes':bundle,'voice_available':False,'browser_vitals':'BLOCKED','method':'Sequential localhost urllib HTTP, 20 samples per GET; no mobile/throttling/browser engine.'}
    (ROOT/'artifacts/phase12-performance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))
    lines=['# Performance baseline and results — 10 October 2026','',
        'These are actual source/build and localhost HTTP measurements, not browser LCP/INP/CLS or mobile results. Browser inspection remains blocked. CPU contention and loopback transport limit generalization.','',
        '## Loader budget','',
        'Phase 12 started with no widget, so the host-page widget baseline was zero bytes. The new loader budget is at most 4096 gzip bytes, enforced by a Node source test. No speech models or large SDKs load on the host. The iframe is lazy; loader CSS is isolated in Shadow DOM. Gzip sizes below are measured source estimates. Actual nginx wire gzip and decompressed equality with the source loader passed in artifacts/phase12-http-security.json.','',
        '| Asset | Raw bytes | Gzip bytes |','|---|---:|---:|']
    for name,size in assets.items():lines.append(f"| {name} | {size['bytes']} | {size['gzip_bytes']} |")
    lines+=['','## HTTP samples','',result['method'],'','| GET | Samples | p50 ms | p95 ms |','|---|---:|---:|---:|']
    for name,sample in samples.items():lines.append(f"| {name} | {sample['n']} | {sample['p50_ms']} | {sample['p95_ms']} |")
    turns=state['message_latency_ms'];lines+=['',f"Six real widget POST turns through mock agents/calendar measured {min(turns):.2f}–{max(turns):.2f} ms, median {statistics.median(turns):.2f} ms. This includes two persisted confirmed bookings; it is not Qwen token latency or production capacity.",'',
        f"Final dashboard assets total {bundle} bytes. Build entry JS: 197.06 kB / 68.56 kB gzip; WidgetView is a separate lazy 9.62 kB chunk. The earlier Phase 11 entry was 186.68 kB, so bilingual widget resources increased the dashboard entry by 10.38 kB. No universal speed improvement is claimed.",'',
        'Asset responses use five-minute cache headers and content-digest ETags; the server does not currently implement conditional 304 handling. JSON session responses remain uncached. No streaming provider is certified, so responses are complete-message HTTP.', '',
        'Targets awaiting actual desktop/mobile and slow-network measurement: LCP ≤2.5 s, INP ≤200 ms, CLS ≤0.1 at p75; bootstrap/time-to-interactive/first-response/retry/error metrics need browser instrumentation. Server request timing and persistent admission/session/message counts provide preliminary diagnostics, not end-user field measurements.','',
        'Evidence: artifacts/phase12-performance.json; artifacts/phase12-journey-state.json; artifacts/phase12-final-frontend-build.txt.']
    (ROOT/'docs/phase12/PERFORMANCE_BASELINE_AND_RESULTS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')

if __name__=='__main__':main()
