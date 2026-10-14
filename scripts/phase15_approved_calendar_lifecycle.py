"""Run INSIDE the existing backend container. Only the named owner-approved test."""
import json
import os
import time
import re
from datetime import datetime, timezone
from urllib.parse import urlsplit, parse_qs
import httpx
from backend.assistant.store import Store
from backend.assistant.security import TenantSecretStore
from backend.assistant.self_hosted import deployment_secret
from backend.assistant.google_workspace import GoogleWorkspace, ACCOUNT
from backend.assistant.domain import Principal

TENANT='a7cfa147-0ded-41a5-a0f1-69b717e9ece8'
BOOKING='53e2ffc5-7296-4fb6-b61f-71d177a11d9f-booking'
store=Store(os.environ['ASSISTANT_DATABASE'])
secret=TenantSecretStore(store,deployment_secret('ASSISTANT_ENCRYPTION_KEY'))
google=GoogleWorkspace(store,secret,lambda:datetime.now(timezone.utc),development=True)
actor=Principal(TENANT,'demo-admin','admin','demo-admin')

def management_token():
    booking=store.get('operations_events',TENANT,BOOKING)
    jobs=[row for row in store.list('jobs',TENANT) if row.get('booking_id')==BOOKING and row.get('subject')=='Управление на демонстрацията' and row['status']=='sent']
    job=jobs[-1]
    body=secret.get(TENANT,'concierge:mail:'+job['id'],actor)
    link=re.search(r'https?://[^\s]+#token=[^\s]+',body).group(0)
    return booking,parse_qs(urlsplit(link).fragment)['token'][0]

def action(booking,token,kind,identity,**kwargs):
    with httpx.Client(timeout=90) as client:
        response=client.post('http://127.0.0.1:8000/widget/v1/manage/'+booking['public_id'],headers={'Origin':'http://127.0.0.1:3020'},json={'token':token,'action':kind,'event_id':identity,'locale':'bg-BG','confirmed':True,**kwargs})
    if response.status_code!=200:raise RuntimeError('Management '+kind+' HTTP '+str(response.status_code))
    return response.json()

def main():
    booking,token=management_token()
    assert booking['email']==ACCOUNT and booking['status']=='confirmed' and booking['starts_at']=='2026-10-14T15:00:00+03:00'
    row=store.find('operations_events',TENANT,'concierge:policy');original=row['policy']
    report={'owner_approved_test':BOOKING,'locale':'bg-BG','target':'2026-10-14T16:00:00+03:00'}
    try:
        store.update('operations_events',TENANT,row['id'],{'policy':{**original,'operations_authorized':True}})
        store.audit(actor,'phase15:approved_calendar_lifecycle_started',resource_id=BOOKING)
        slots=action(booking,token,'availability','phase15-owner-availability',day='2026-10-14')
        if report['target'] not in slots['slots']:raise RuntimeError('Approved reschedule slot unavailable')
        changed=action(booking,token,'reschedule','phase15-owner-reschedule',starts_at=report['target'])
        replay=action(booking,token,'reschedule','phase15-owner-reschedule',starts_at=report['target'])
        report['reschedule']=changed['data'];report['reschedule_replay_duplicate']=replay.get('duplicate',False)
        read=google.call(TENANT,'calendar','GET','calendars/primary/events/'+booking['event_id'])
        assert read.status_code==200 and read.json()['start']['dateTime']==report['target']
        report['google_reschedule_readback']='PASS'
        for _ in range(15):
            jobs=[j for j in store.list('jobs',TENANT) if j.get('booking_id')==BOOKING and j.get('subject')=='Управление на демонстрацията']
            if jobs[-1]['status']=='sent':break
            time.sleep(2)
        booking,token=management_token()
        assert booking['starts_at']==report['target']
        cancelled=action(booking,token,'cancel','phase15-owner-cancel')
        replay=action(booking,token,'cancel','phase15-owner-cancel')
        report['cancel']=cancelled['data'];report['cancel_replay_duplicate']=replay.get('duplicate',False)
        read=google.call(TENANT,'calendar','GET','calendars/primary/events/'+booking['event_id'])
        assert read.status_code==404 or read.status_code==200 and read.json().get('status')=='cancelled'
        report['google_cancel_readback']='PASS'
        jobs=[j for j in store.list('jobs',TENANT) if j.get('booking_id')==BOOKING]
        report['email_jobs']=[{'subject':j['subject'],'status':j['status'],'due_at':j['due_at']} for j in jobs]
        assert not any(j['status']=='pending' for j in jobs)
        appointment=store.find('appointments',TENANT,'concierge:'+BOOKING)
        report['dashboard_status']=appointment['status'];report['inbox_delivery']='OWNER_REVIEW_REQUIRED'
        print(json.dumps(report,ensure_ascii=False))
    finally:
        store.update('operations_events',TENANT,row['id'],{'policy':original})
        store.audit(actor,'phase15:approved_calendar_lifecycle_finished',resource_id=BOOKING)

if __name__=='__main__':
    try:main()
    except Exception as error:
        print(json.dumps({'result':'FAILED','error_type':type(error).__name__}))
        raise SystemExit(1) from None
