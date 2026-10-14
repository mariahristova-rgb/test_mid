// Opt-in local audit only. No URLs, attribution, transcripts or outbound telemetry.
import { onCLS, onINP, onLCP } from 'web-vitals';
let started=false;
export function safeMetric(metric) {
  if (!['LCP','INP','CLS'].includes(metric.name) || !Number.isFinite(metric.value) || metric.value<0) return null;
  return {name:metric.name,value:metric.value};
}
export function startLocalVitals() {
  if(started)return;started=true;
  const initialViewport={width:innerWidth,height:innerHeight};
  const metrics={};
  const record=metric=>{
    const safe=safeMetric(metric);if(!safe)return;
    metrics[safe.name]=safe.value;
    document.documentElement.dataset.localPerformance=JSON.stringify({method:'web-vitals-local-opt-in',initialViewport,reportedViewport:{width:innerWidth,height:innerHeight},metrics});
  };
  onLCP(record,{reportAllChanges:true});onINP(record,{reportAllChanges:true});onCLS(record,{reportAllChanges:true});
}
