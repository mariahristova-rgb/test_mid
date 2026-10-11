import {conciergeLabels} from './concierge-labels.js';
const id=document.querySelector('meta[name="public-id"]').content;
const token=new URLSearchParams(location.hash.slice(1)).get('token')||'';
history.replaceState(history.state,'',location.pathname);
let locale=navigator.language.toLowerCase().startsWith('bg')?'bg-BG':'en-US',pending=null,busy=false,explicit=false;
const byId=name=>document.getElementById(name),t=key=>conciergeLabels[locale][key]||conciergeLabels[locale].failed;
function language(){document.documentElement.lang=locale;byId('language').value=locale;byId('language').setAttribute('aria-label',locale==='bg-BG'?'Език':'Language');for(const [id,key] of Object.entries({'date-label':'day','time-label':'time','consent-label':'consent',reschedule:'reschedule',cancel:'cancel'}))byId(id).textContent=t(key);}
async function api(body){const response=await fetch('/widget/v1/manage/'+id,{method:'POST',credentials:'omit',headers:{'Content-Type':'application/json'},body:JSON.stringify({token,locale,event_id:crypto.randomUUID(),...body})});const result=await response.json();if(!response.ok)throw Object.assign(new Error(),{code:result.code});return result;}
async function run(action){if(busy)return;busy=true;byId('error').textContent='';try{await action();}catch(e){byId('error').textContent=t(e.code);}finally{busy=false;}}
byId('language').addEventListener('change',()=>{locale=byId('language').value;explicit=true;language();});
byId('day').addEventListener('change',()=>void run(async()=>{const result=await api({action:'availability',day:byId('day').value});byId('slots').replaceChildren();for(const slot of result.slots){const node=document.createElement('option');node.value=slot;node.textContent=new Intl.DateTimeFormat(locale,{timeZone:'Europe/Sofia',dateStyle:'medium',timeStyle:'short'}).format(new Date(slot));byId('slots').append(node);}if(!result.slots.length)byId('status').textContent=t('empty');}));
for(const action of ['reschedule','cancel'])byId(action).addEventListener('click',()=>void run(async()=>{
  if(!byId('consent').checked)throw Object.assign(new Error(),{code:'required'});
  pending=pending||{action,confirmed:true,starts_at:action==='reschedule'?byId('slots').value:null,event_id:crypto.randomUUID()};
  const result=await api(pending);pending=null;byId('status').textContent=t(result.data.status==='cancelled'?'cancelled':'confirmed');byId('manage').hidden=true;
}));
language();void run(async()=>{const result=await api({action:'details'});if(!explicit)locale=result.locale;language();byId('status').textContent=new Intl.DateTimeFormat(locale,{timeZone:'Europe/Sofia',dateStyle:'medium',timeStyle:'short'}).format(new Date(result.starts_at));});
