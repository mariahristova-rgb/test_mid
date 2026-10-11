import {conciergeLabels} from './concierge-labels.js';
const make=(tag,text)=>{const node=document.createElement(tag);if(text)node.textContent=text;return node;};
export function startConcierge({api,locale,bubble,send,id}){
  const root=document.getElementById('workflow');let mode='',fields={},verification='',emailVerified=false,managementToken='',pending=null,busy=false,capabilities=null;
  const t=key=>conciergeLabels[locale()][key]||conciergeLabels[locale()].failed;
  const status=make('p');status.setAttribute('role','status');const error=make('p');error.setAttribute('role','alert');
  function field(form,key,type='text',required=false){const label=make('label',t(key)),input=make('input');input.type=type;input.required=required;input.maxLength=key==='topic'?1500:250;if(key==='link')input.maxLength=2500;input.setAttribute('aria-label',t(key));label.append(input);form.append(label);fields[key]=input;return input;}
  function button(form,key,action){const node=make('button',t(key));node.type='button';node.addEventListener('click',()=>void run(action));form.append(node);return node;}
  async function run(action){if(busy)return;busy=true;error.textContent='';for(const node of root.querySelectorAll('button'))node.disabled=true;try{await action();}catch(e){error.textContent=t(e.code)||t('failed');if(['slot_unavailable','outside_booking_window','verification_required','invalid_input','ownership_required','live_operations_not_authorized','google_not_connected','stale_event'].includes(e.code))pending=null;}finally{busy=false;for(const node of root.querySelectorAll('button'))node.disabled=false;}}
  function request(tool,arguments_){return {tool,arguments:arguments_,locale:locale(),event_id:crypto.randomUUID()};}
  async function action(tool,arguments_){const body=request(tool,arguments_);return (await api('v1/actions',body)).data;}
  async function management(action,extra={}){return api('v1/manage',{token:managementToken,action,event_id:crypto.randomUUID(),locale:locale(),...extra});}
  async function dates(form,owned=false){const day=field(form,'day','date',true),label=make('label',t('time')),select=make('select');select.required=true;select.setAttribute('aria-label',t('time'));fields.starts_at=select;label.append(select);form.append(label);day.max=capabilities?.ends_on||'2026-12-31';day.min=new Intl.DateTimeFormat('en-CA',{timeZone:'Europe/Sofia',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
    day.addEventListener('change',()=>void run(async()=>{const result=owned?await management('availability',{day:day.value}):await action('ConciergeAvailability',{day:day.value});select.replaceChildren();for(const slot of result.slots){const option=make('option',new Intl.DateTimeFormat(locale(),{timeZone:'Europe/Sofia',dateStyle:'medium',timeStyle:'short'}).format(new Date(slot)));option.value=slot;select.append(option);}if(!result.slots.length)status.textContent=t('empty');}));
  }
  function codeFields(form){field(form,'email','email',true);field(form,'code','text');button(form,'verify',async()=>{const result=await api('v1/verify-email',{email:fields.email.value,locale:locale()});verification=result.verification_id;emailVerified=false;status.textContent=t('verification');});button(form,'checkCode',async()=>{await api('v1/verify-email',{verification_id:verification,code:fields.code.value,locale:locale()});emailVerified=true;status.textContent=t('verified');});fields.email.addEventListener('input',()=>{verification='';emailVerified=false;});}
  async function open(actionName){
    if(pending){error.textContent=t('delivery_unknown');return;}
    mode=actionName;fields={};verification='';emailVerified=false;managementToken='';root.replaceChildren();root.hidden=false;error.textContent='';status.textContent='';
    root.append(make('h2',t(mode)),status,error);const back=make('button',t('back'));back.type='button';back.addEventListener('click',()=>{if(!pending)root.hidden=true;});root.append(back);
    const form=make('form');form.noValidate=true;root.append(form);
    if(mode==='booking'){
      capabilities=await api('v1/concierge');
      if(!capabilities.booking_available){status.textContent=t('unavailable');return;}
      form.append(make('p',t('hours')));await dates(form);field(form,'name','text',true);codeFields(form);field(form,'topic','text',true);field(form,'company');
    }else if(mode==='cancel'||mode==='reschedule'){
      form.append(make('p',t('ownership')));field(form,'link','url',true);button(form,'load',async()=>{
        const url=new URL(fields.link.value);
        if(url.origin!==location.origin||url.pathname!=='/widget/manage/'+id)throw Object.assign(new Error(),{code:'ownership_required'});
        managementToken=new URLSearchParams(url.hash.slice(1)).get('token')||'';
        const result=await management('details');status.textContent=new Intl.DateTimeFormat(locale(),{timeZone:'Europe/Sofia',dateStyle:'medium',timeStyle:'short'}).format(new Date(result.starts_at));
        if(mode==='reschedule'&&!fields.day)await dates(form,true);
      });
    }else{
      field(form,'name','text',mode!=='feature');
      if(mode==='information')codeFields(form);else field(form,'email','email',mode!=='feature');
      field(form,'company','text',mode==='business');field(form,'topic','text',true);
      if(mode==='business')field(form,'timeline');if(mode==='feature')field(form,'impact','text',true);
      if(mode==='information')field(form,'marketing','checkbox');
    }
    field(form,'consent','checkbox',true);const submit=make('button',t('submit'));submit.type='submit';form.append(submit);
    if(mode==='cancel'||mode==='reschedule'){
      const details=make('details'),summary=make('summary',t('recover'));details.append(summary);root.append(details);const recovery=make('form');recovery.noValidate=true;details.append(recovery);
      field(recovery,'receipt','text',true);codeFields(recovery);
      button(recovery,'recover',async()=>{if(!recovery.checkValidity()||!emailVerified)throw Object.assign(new Error(),{code:'verification_required'});await api('v1/recover',{booking_id:fields.receipt.value,email:fields.email.value,verification_id:verification,locale:locale()});status.textContent=t('queued');});
      recovery.addEventListener('submit',event=>event.preventDefault());
    }
    form.addEventListener('submit',event=>{event.preventDefault();void run(async()=>{
      if(!form.checkValidity()){error.textContent=t('required');return;}
      if(!pending){
        if(mode==='booking'||mode==='information'){if(!emailVerified)throw Object.assign(new Error(),{code:'verification_required'});}
        if(mode==='cancel'||mode==='reschedule'){
          if(!managementToken)throw Object.assign(new Error(),{code:'ownership_required'});
          pending={path:'v1/manage',body:{token:managementToken,action:mode,starts_at:fields.starts_at?.value||null,confirmed:true,event_id:crypto.randomUUID(),locale:locale()}};
        }else{
          const args=mode==='booking'?{starts_at:fields.starts_at.value,name:fields.name.value,email:fields.email.value,company:fields.company.value,topic:fields.topic.value,verification_id:verification,consent:true}:
            {action:mode,name:fields.name.value,email:fields.email.value,company:fields.company.value,topic:fields.topic.value,timeline:fields.timeline?.value||'',impact:fields.impact?.value||'',verification_id:verification,consent:true,marketing_consent:fields.marketing?.checked||false};
          pending={path:'v1/actions',body:request(mode==='booking'?'ConciergeBooking':'ConciergeRequest',args)};
        }
      }
      const result=await api(pending.path,pending.body);pending=null;const data=result.data;
      let message=data.status==='confirmed'?t('confirmed'):data.status==='cancelled'?t('cancelled'):t('queued');
      if(data.starts_at)message+=' '+new Intl.DateTimeFormat(locale(),{timeZone:'Europe/Sofia',dateStyle:'medium',timeStyle:'short'}).format(new Date(data.starts_at))+' · Europe/Sofia';
      if(data.booking_id)message+=' '+t('receipt')+': '+data.booking_id;
      bubble(message,'assistant');status.textContent=message;form.replaceChildren();
      if(data.meet_url){const url=new URL(data.meet_url);if(url.protocol==='https:'&&url.hostname==='meet.google.com'){const link=make('a','Google Meet');link.href=url.href;link.rel='noopener noreferrer';link.target='_blank';form.append(link);}}
    });});
    root.focus();
  }
  for(const button of document.querySelectorAll('[data-action]'))button.addEventListener('click',()=>{
    if(busy)return;
    const name=button.dataset.action;
    if(name==='explore'){void send(false,locale()==='bg-BG'?'Какво е Ontelyx?':'What is Ontelyx?');return;}
    void run(()=>open(name));
  });
  return {language(){for(const node of document.querySelectorAll('[data-concierge]'))node.textContent=t(node.dataset.concierge);if(!pending){root.hidden=true;root.replaceChildren();}},hasPending:()=>!!pending};
}
