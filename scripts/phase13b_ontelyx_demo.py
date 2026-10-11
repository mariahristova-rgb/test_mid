"""Provision/verify only the dedicated synthetic Ontelyx website demo tenant.

Uses existing SaaS/draft/widget APIs. Never deploys a public site, copies backend
code to the website, sends contact messages or stores credentials in reports.
"""
import argparse
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
from time import perf_counter
import urllib.error
from uuid import uuid4
from phase12_local_journey import ROOT,BASE,WIDGET,request

SITE='http://127.0.0.1:5173'
DIRECTORY=ROOT/'artifacts/phase13b'
WEBSITE=DIRECTORY/'ontelyx'
STATE=DIRECTORY/'demo-state.json'
CONFIG=ROOT/'semantic_os/config/ontelyx_public_demo.json'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','verify']);args=parser.parse_args()
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token']}
    if args.stage=='prepare':
        if STATE.exists():raise SystemExit('Existing demo state: review before reprovisioning; use verify.')
        public=json.loads(CONFIG.read_text(encoding='utf-8'))
        tenant=request(BASE,'/api/saas/register',staff,{'name':public['name'],'email':'demo-owner@ontelyx-demo.example','default_locale':public['default_locale'],'timezone':public['timezone'],'plan_id':'sandbox','event_id':'ontelyx-'+str(uuid4())})
        headers={**staff,'X-Tenant-ID':tenant['tenant_id']}
        token=request(BASE,'/api/saas/onboarding/mock-email',headers)['token']
        request(BASE,'/api/saas/onboarding/verify',headers,{'token':token})
        request(BASE,'/api/billing/trial',headers,{'confirmed':True,'plan_id':'sandbox','event_id':'ontelyx-trial'})
        assistant=request(BASE,'/api/assistants',headers)[0]
        config={key:value for key,value in assistant.items() if key not in ('id','tenant_id')}
        config.update(instructions=public['instructions'],name=public['name'],default_locale=public['default_locale'],faq_entries=public['faq_entries'],allowed_tools=public['allowed_tools'],enabled_channels=['web_chat'],llm_provider='mock')
        draft=request(BASE,'/api/ux/drafts',headers,{'assistant_id':assistant['id'],'config':config,'business':{'name':public['name'],'website':'https://www.ontelyx.tech/','industry':'Synthetic product demo','timezone':public['timezone'],'service':'Fictional product demonstration'}})
        state={'tenant_id':tenant['tenant_id'],'assistant_id':assistant['id'],'draft_id':draft['id'],'revision':draft['revision'],'site_origin':SITE,'sandbox':[],'state':'preparing'}
        STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous','faq','language_switch','handoff'):
                receipt=request(BASE,f"/api/ux/drafts/{draft['id']}/tests",headers,{'revision':draft['revision'],'scenario':scenario,'locale':locale})
                state['sandbox'].append({'scenario':scenario,'locale':locale,'verdict':receipt['verdict']})
                STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
                if receipt['verdict']!='PASS':raise RuntimeError('Failed sandbox '+scenario+' '+locale)
        request(BASE,f"/api/ux/drafts/{draft['id']}/publish",headers,{'revision':draft['revision'],'confirmed':True})
        widget=request(BASE,'/api/widgets',headers,{**{key:public[key] for key in ('greetings','privacy_notices','color','appearance','retention_days','daily_sessions','daily_messages')},'assistant_id':assistant['id'],'origins':[SITE],'faq_approved':True})
        proof=request(BASE,f"/api/widgets/{widget['id']}/challenge",headers,{'origin':SITE})
        proof_path=WEBSITE/'public'/proof['path'].lstrip('/');proof_path.parent.mkdir(parents=True,exist_ok=True);proof_path.write_text(proof['content'],encoding='ascii')
        # Only a public ID and public origin are written to ignored local build config.
        (WEBSITE/'.env.local').write_text('VITE_ASSISTANT_WIDGET_ORIGIN='+WIDGET+'\nVITE_ASSISTANT_PUBLIC_ID='+widget['public_id']+'\n',encoding='utf-8')
        state.update(widget_id=widget['id'],public_id=widget['public_id'],state='prepared');STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        print('Prepared dedicated synthetic tenant and public local website config. Build the website before verify.');return
    state=json.loads(STATE.read_text());headers={**staff,'X-Tenant-ID':state['tenant_id']}
    if state['state']=='HTTP_PASS_BROWSER_PENDING':print('Recorded journey already passed; no duplicate booking.');return
    request(BASE,f"/api/widgets/{state['widget_id']}/verify",headers,{'origin':SITE})
    widget=request(BASE,f"/api/widgets/{state['widget_id']}/publish",headers,{'draft_id':state['draft_id'],'confirmed':True})
    version=widget['active_version'];latencies=[]
    day=datetime.now(timezone.utc).date()+timedelta(days=2)
    while day.weekday()>4:day+=timedelta(days=1)
    public=json.loads(CONFIG.read_text(encoding='utf-8'))
    for index,locale in enumerate(('bg-BG','en-US')):
        ticket=request(WIDGET,'/widget/admission/'+state['public_id'],{'Origin':SITE},{'locale':locale})
        session=request(WIDGET,'/widget/redeem/'+state['public_id'],{'Origin':WIDGET},{'ticket':ticket['ticket'],'parent_origin':SITE,'locale':locale})
        assert session['voice_available'] is False
        visitor={'Origin':WIDGET,'Authorization':'Bearer '+session['session_token']}
        question=public['faq_entries'][0]['question_bg' if index==0 else 'question_en']
        answer=request(WIDGET,'/widget/messages/'+state['public_id'],visitor,{'content':question,'event_id':'faq','locale':locale})
        assert answer['response']==public['faq_entries'][0]['answer_bg' if index==0 else 'answer_en']
        hour=15+index
        texts=[f"Искам да запиша час на {day.strftime('%d.%m.%Y')} {hour}:00.",'Казвам се Демо Клиент.','Да, потвърждавам.'] if index==0 else [f"Book an appointment on {day.strftime('%m/%d/%Y')} {hour-12}:00 PM.",'My name is Demo Visitor.','Yes, confirm.']
        for turn,text in enumerate(texts):
            message={'content':text,'event_id':f'booking{turn}','locale':locale};started=perf_counter()
            result=request(WIDGET,'/widget/messages/'+state['public_id'],visitor,message);latencies.append(round((perf_counter()-started)*1000,2))
        assert result['booking_status']=='completed'
        assert request(WIDGET,'/widget/messages/'+state['public_id'],visitor,message)['duplicate']
        switched='en-US' if locale=='bg-BG' else 'bg-BG'
        switch='Switch to English.' if switched=='en-US' else 'Премини на български.'
        assert request(WIDGET,'/widget/messages/'+state['public_id'],visitor,{'content':switch,'event_id':'switch'})['locale']==switched
    appointments=request(BASE,'/api/appointments',headers);assert len(appointments)==2
    diagnostics=[request(BASE,f"/api/ux/conversations/{row['conversation_id']}/diagnostics",headers) for row in appointments]
    assert all(any(event['kind']=='agent_handoff' for event in row['timeline']) for row in diagnostics)
    try:request(WIDGET,'/widget/admission/'+state['public_id'],{'Origin':'https://unapproved.example'},{'locale':'auto'})
    except urllib.error.HTTPError as error:assert error.code==403
    else:raise RuntimeError('Unapproved origin admitted')
    request(BASE,f"/api/widgets/{state['widget_id']}/unpublish",headers,{'confirmed':True})
    try:request(WIDGET,'/widget/admission/'+state['public_id'],{'Origin':SITE},{'locale':'auto'})
    except urllib.error.HTTPError as error:assert error.code==403
    else:raise RuntimeError('Unpublished admission allowed')
    request(BASE,f"/api/widgets/{state['widget_id']}/rollback",headers,{'confirmed':True,'version_id':version})
    state.update(state='HTTP_PASS_BROWSER_PENDING',booking_date=day.isoformat(),booking_ids=[row['id'] for row in appointments],message_latency_ms=latencies,voice_available=False,providers='MOCK',browser_acceptance='BLOCKED')
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8');print(json.dumps(state,indent=2))

if __name__=='__main__':main()
