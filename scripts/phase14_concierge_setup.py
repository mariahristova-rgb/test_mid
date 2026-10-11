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
DIRECTORY=ROOT/'artifacts/phase14'
WEBSITE=ROOT/'artifacts/phase13b/ontelyx'
STATE=DIRECTORY/'demo-state.json'
CONFIG=ROOT/'semantic_os/config/ontelyx_concierge.json'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','verify']);args=parser.parse_args()
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token']}
    if args.stage=='prepare':
        if STATE.exists():raise SystemExit('Existing demo state: review before reprovisioning; use verify.')
        public=json.loads(CONFIG.read_text(encoding='utf-8'))
        tenant=request(BASE,'/api/saas/register',staff,{'name':public['name'],'email':'demo-owner@ontelyx-demo.example','default_locale':public['default_locale'],'timezone':public['timezone'],'plan_id':'sandbox','event_id':'concierge-'+str(uuid4())})
        headers={**staff,'X-Tenant-ID':tenant['tenant_id']}
        token=request(BASE,'/api/saas/onboarding/mock-email',headers)['token']
        request(BASE,'/api/saas/onboarding/verify',headers,{'token':token})
        request(BASE,'/api/billing/trial',headers,{'confirmed':True,'plan_id':'sandbox','event_id':'ontelyx-trial'})
        request(BASE,'/api/concierge/policy',headers,{'enabled':True,'management_origin':WIDGET,'operations_authorized':False},method='PUT')
        assistant=request(BASE,'/api/assistants',headers)[0]
        config={key:value for key,value in assistant.items() if key not in ('id','tenant_id')}
        config.update(instructions=public['instructions'],name=public['name'],default_locale=public['default_locale'],faq_entries=public['faq_entries'],allowed_tools=public['allowed_tools'],enabled_channels=['web_chat'],llm_provider='mock',public_knowledge_only=True)
        draft=request(BASE,'/api/ux/drafts',headers,{'assistant_id':assistant['id'],'config':config,'business':{'name':public['name'],'website':'https://www.ontelyx.tech/','industry':'Ontelyx product concierge','opens':'10:00','closes':'19:00','timezone':public['timezone'],'service':'Fictional product demonstration'}})
        state={'tenant_id':tenant['tenant_id'],'assistant_id':assistant['id'],'draft_id':draft['id'],'revision':draft['revision'],'site_origin':SITE,'sandbox':[],'state':'preparing'}
        STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        for locale in ('bg-BG','en-US'):
            for scenario in ('greeting','faq'):
                receipt=request(BASE,f"/api/ux/drafts/{draft['id']}/tests",headers,{'revision':draft['revision'],'scenario':scenario,'locale':locale})
                state['sandbox'].append({'scenario':scenario,'locale':locale,'verdict':receipt['verdict']})
                STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
                if receipt['verdict']!='PASS':raise RuntimeError('Failed sandbox '+scenario+' '+locale)
        request(BASE,f"/api/ux/drafts/{draft['id']}/publish",headers,{'revision':draft['revision'],'confirmed':True})
        widget=request(BASE,'/api/widgets',headers,{**{key:public[key] for key in ('greetings','privacy_notices','color','appearance','retention_days','daily_sessions','daily_messages')},'assistant_id':assistant['id'],'origins':[SITE],'faq_approved':True,'concierge_enabled':True,'booking_enabled':False})
        proof=request(BASE,f"/api/widgets/{widget['id']}/challenge",headers,{'origin':SITE})
        proof_path=WEBSITE/'public'/proof['path'].lstrip('/');proof_path.parent.mkdir(parents=True,exist_ok=True);proof_path.write_text(proof['content'],encoding='ascii')
        # Only a public ID and public origin are written to ignored local build config.
        (WEBSITE/'.env.local').write_text('VITE_ASSISTANT_WIDGET_ORIGIN='+WIDGET+'\nVITE_ASSISTANT_PUBLIC_ID='+widget['public_id']+'\n',encoding='utf-8')
        state.update(widget_id=widget['id'],public_id=widget['public_id'],state='prepared');STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        print('Prepared dedicated synthetic tenant and public local website config. Build the website before verify.');return
    state=json.loads(STATE.read_text());headers={**staff,'X-Tenant-ID':state['tenant_id']}
    request(BASE,f"/api/widgets/{state['widget_id']}/verify",headers,{'origin':SITE})
    request(BASE,f"/api/widgets/{state['widget_id']}/publish",headers,{'draft_id':state['draft_id'],'confirmed':True})
    state.update(state='LOCAL_CONFIGURED_GOOGLE_NOT_CONNECTED',live_operations_authorized=False,google_account='mariya.manolova92@gmail.com',calendar='primary',live_google_test='NOT_RUN')
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8');print(json.dumps(state,indent=2))

if __name__=='__main__':main()
