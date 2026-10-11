"""Authorized fictional customer HTTP journey. No browser acceptance claims.

Writes only the new tenant and ignored local sample-site/evidence files.
Visitor/staff credentials remain in memory; reports contain no secrets.
"""
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from time import perf_counter
import urllib.request
import urllib.error
from uuid import uuid4

ROOT=Path(__file__).resolve().parents[1]
BASE='http://127.0.0.1:3017/backend'
WIDGET='http://127.0.0.1:3020'
SITE='http://127.0.0.1:3021'
STATE=ROOT/'artifacts/phase12-journey-state.json'

def request(base,path,headers=None,data=None,method=None):
    body=json.dumps(data,ensure_ascii=False).encode() if data is not None else None
    req=urllib.request.Request(base+path,data=body,method=method,headers={'Content-Type':'application/json',**(headers or {})})
    with urllib.request.urlopen(req,timeout=40) as response:
        return json.load(response)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['prepare','verify']);args=parser.parse_args()
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token']}
    if args.stage=='prepare':
        if STATE.exists():
            state=json.loads(STATE.read_text(encoding='utf-8'));headers={**staff,'X-Tenant-ID':state['tenant_id']}
            if state.get('integration_id'):print('Existing integration prepared; run verify.');return
            assistant={'id':state['assistant_id']}
            draft=next(row for row in request(BASE,'/api/ux/drafts',headers) if row['id']==state['draft_id'])
        else:
            tenant=request(BASE,'/api/saas/register',staff,{'name':'Fictional Widget Clinic','email':'owner@fictional-widget.example','default_locale':'bg-BG','timezone':'Europe/Sofia','plan_id':'sandbox','event_id':'phase12-'+str(uuid4())})
            headers={**staff,'X-Tenant-ID':tenant['tenant_id']}
            verification=request(BASE,'/api/saas/onboarding/mock-email',headers)
            request(BASE,'/api/saas/onboarding/verify',headers,{'token':verification['token']})
            request(BASE,'/api/billing/trial',headers,{'confirmed':True,'plan_id':'sandbox','event_id':'phase12-trial'})
            assistant=request(BASE,'/api/assistants',headers)[0]
            config={key:value for key,value in assistant.items() if key not in ('id','tenant_id')}
            config.update(name='Fictional bilingual receptionist',instructions='Use approved FAQs. Request details and explicit consent before booking.',enabled_channels=['web_chat'],allowed_tools=['CheckAvailability','CreateAppointment','EscalateToHuman'],llm_provider='mock',
                faq_entries=[{'question_bg':'Какво е работното време?','answer_bg':'Работим от понеделник до петък от 09:00 до 18:00.','question_en':'What are your opening hours?','answer_en':'We open Monday to Friday from 09:00 to 18:00.'}])
            draft=request(BASE,'/api/ux/drafts',headers,{'assistant_id':assistant['id'],'config':config,'business':{'name':'Fictional Widget Clinic','website':SITE,'industry':'Demo clinic','timezone':'Europe/Sofia'}})
            state={'tenant_id':tenant['tenant_id'],'draft_id':draft['id'],'revision':draft['revision'],'assistant_id':assistant['id'],'receipts':[]}
            STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        for language in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous','faq'):
                result=request(BASE,f"/api/ux/drafts/{draft['id']}/tests",headers,{'revision':draft['revision'],'locale':language,'scenario':scenario})
                if result['verdict']!='PASS':raise RuntimeError('Sandbox '+scenario+' failed')
                state['receipts'].append({'scenario':scenario,'locale':language,'status':result['verdict']})
        request(BASE,f"/api/ux/drafts/{draft['id']}/publish",headers,{'revision':draft['revision'],'confirmed':True})
        integration=request(BASE,'/api/widgets',headers,{'assistant_id':assistant['id'],'origins':[SITE],'greetings':{'bg-BG':'Здравейте! Това е демонстрационен чат.','en-US':'Hello! This is a demonstration chat.'},'privacy_notices':{'bg-BG':'Само измислени данни. Чатът се пази 7 дни; записванията са в демо календар.','en-US':'Use fictional data only. Chat is retained for 7 days; bookings use a demo calendar.'},'faq_approved':True})
        proof=request(BASE,f"/api/widgets/{integration['id']}/challenge",headers,{'origin':SITE})
        installation=request(BASE,f"/api/widgets/{integration['id']}/installation",headers)
        directory=ROOT/'artifacts/phase12-site';directory.mkdir(exist_ok=True)
        nonce=directory/proof['path'].lstrip('/');nonce.parent.mkdir(parents=True,exist_ok=True);nonce.write_text(proof['content'],encoding='ascii')
        template=(ROOT/'tests/examples/widget-site/index.html').read_text(encoding='utf-8')
        (directory/'index.html').write_text(template.replace('{{EMBED_SNIPPET}}',installation['snippet']),encoding='utf-8')
        state.update(integration_id=integration['id'],public_id=integration['public_id']);STATE.write_text(json.dumps(state,indent=2),encoding='utf-8')
        print('Prepared fictional tenant and sample website. No visitor booking yet.')
        return
    state=json.loads(STATE.read_text());headers={**staff,'X-Tenant-ID':state['tenant_id']}
    if state.get('status')=='HTTP_JOURNEY_PASS_BROWSER_UNVERIFIED':print('Recorded journey already passed; no repeat booking.');return
    saved=next(row for row in request(BASE,'/api/widgets',headers) if row['id']==state['integration_id'])
    if saved['domains'].get(SITE,{}).get('state')!='verified':request(BASE,f"/api/widgets/{state['integration_id']}/verify",headers,{'origin':SITE})
    integration=request(BASE,f"/api/widgets/{state['integration_id']}/publish",headers,{'draft_id':state['draft_id'],'confirmed':True})
    version=integration['active_version'];latencies=[]
    target=datetime.now(timezone.utc).date()+timedelta(days=2)
    while target.weekday()>4:target+=timedelta(days=1)
    state['booking_date']=target.isoformat()
    for index,locale in enumerate(('bg-BG','en-US')):
        ticket=request(WIDGET,'/widget/admission/'+state['public_id'],{'Origin':SITE},{'locale':'auto'})
        visitor=request(WIDGET,'/widget/redeem/'+state['public_id'],{'Origin':WIDGET},{'ticket':ticket['ticket'],'parent_origin':SITE,'locale':locale})
        browser={'Origin':WIDGET,'Authorization':'Bearer '+visitor['session_token']}
        date=target.isoformat();hour=15+index
        inputs=[f"Искам да запиша час на {target.strftime('%d.%m.%Y')} {hour}:00.",'Казвам се Иван Иванов.','Да, потвърждавам.'] if locale=='bg-BG' else [f"Book an appointment on {target.strftime('%m/%d/%Y')} {hour-12}:00 PM.",'My name is Jane Smith.','Yes, confirm.']
        for number,text in enumerate(inputs):
            body={'content':text,'event_id':f'journey_{number}','locale':locale};start=perf_counter()
            result=request(WIDGET,'/widget/messages/'+state['public_id'],browser,body);latencies.append(round((perf_counter()-start)*1000,2))
        if result['booking_status']!='completed':raise RuntimeError('Booking did not complete in '+locale)
        duplicate=request(WIDGET,'/widget/messages/'+state['public_id'],browser,body)
        if not duplicate['duplicate']:raise RuntimeError('Duplicate action was not prevented')
    bookings=request(BASE,'/api/appointments',headers)
    if len(bookings)!=2:raise RuntimeError('Expected exactly two new-tenant bookings')
    conversations=request(BASE,'/api/conversations',headers)
    booked_conversations={row['conversation_id'] for row in bookings}
    diagnostics=[request(BASE,f"/api/ux/conversations/{item['id']}/diagnostics",headers) for item in conversations if item['id'] in booked_conversations]
    if not all(any(event['kind']=='agent_handoff' for event in row['timeline']) for row in diagnostics):raise RuntimeError('Missing handoff')
    request(BASE,f"/api/widgets/{state['integration_id']}/unpublish",headers,{'confirmed':True})
    try:request(WIDGET,'/widget/admission/'+state['public_id'],{'Origin':SITE},{'locale':'auto'})
    except urllib.error.HTTPError as error:
        if error.code!=403:raise
    else:raise RuntimeError('Unpublished admission remained available')
    request(BASE,f"/api/widgets/{state['integration_id']}/rollback",headers,{'confirmed':True,'version_id':version})
    state.update(status='HTTP_JOURNEY_PASS_BROWSER_UNVERIFIED',booking_ids=[row['id'] for row in bookings],conversation_count=len(conversations),message_latency_ms=latencies,calendar='MOCK',llm='MOCK',email_verification='MOCK',billing='MOCK',desktop_mobile_acceptance='BLOCKED')
    STATE.write_text(json.dumps(state,indent=2),encoding='utf-8');print(json.dumps(state,indent=2))

if __name__=='__main__':main()
