"""Complete the explicitly approved single live booking with the owner's email code."""
import json
import sys
import time
from phase12_local_journey import ROOT,BASE,WIDGET,request

def main():
    state=json.loads((ROOT/'artifacts/local-demo/secrets/phase14-live-session.json').read_text())
    code=sys.stdin.readline().strip()
    if len(code)!=6 or not code.isdigit():raise ValueError('Six-digit code required')
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token'],'X-Tenant-ID':state['tenant_id']}
    visitor={'Origin':WIDGET,'Authorization':'Bearer '+state['session_token']}
    public_id=state['public_id']
    request(WIDGET,'/widget/v1/verify-email/'+public_id,visitor,{'verification_id':state['verification_id'],'code':code,'locale':'bg-BG'})
    policy=request(BASE,'/api/concierge/policy',staff)
    payload={'tool':'ConciergeBooking','arguments':{'starts_at':state['starts_at'],'name':'Mariya Manolova','email':state['email'],'topic':'Owner-approved Ontelyx live acceptance demo','company':'','verification_id':state['verification_id'],'consent':True},'event_id':'owner-live-booking-20261014-1500','locale':'bg-BG'}
    try:
        request(BASE,'/api/concierge/policy',staff,{**policy,'operations_authorized':True},method='PUT')
        result=request(WIDGET,'/widget/v1/actions/'+public_id,visitor,payload)
        repeated=request(WIDGET,'/widget/v1/actions/'+public_id,visitor,payload)
        booking_id=result['data']['booking_id']
        appointments=request(BASE,'/api/appointments',staff)
        matching=[r for r in appointments if r.get('concierge_booking_id')==booking_id]
        assert len(matching)==1 and repeated['duplicate']
        jobs=[]
        for _ in range(15):
            jobs=request(BASE,'/api/concierge/email-jobs',staff)
            if sum(j['status']=='sent' for j in jobs)>=2:break
            time.sleep(2)
        report={'date':'2026-10-14','time':'15:00–15:30','timezone':'Europe/Sofia','booking_id':booking_id,'status':result['data']['status'],'dashboard_appointments':len(matching),'duplicate_request_prevented':repeated['duplicate'],'google_event_id':matching[0].get('google_event_id'),'email_jobs':[{'status':j['status'],'due_at':j['due_at'],'error_code':j.get('error_code')} for j in jobs],'inbox_receipt':'OWNER_REVIEW_REQUIRED'}
        (ROOT/'artifacts/phase14/live-booking-result.json').write_text(json.dumps(report,indent=2))
        print(json.dumps(report,indent=2))
    finally:
        request(BASE,'/api/concierge/policy',staff,policy,method='PUT')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Live confirmation stopped: '+type(error).__name__)
        raise SystemExit(1) from None
