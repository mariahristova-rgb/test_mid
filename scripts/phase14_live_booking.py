"""Owner-approved live test, preserving the public email ownership check."""
import json
import time
from phase12_local_journey import ROOT,BASE,WIDGET,request

EMAIL='mariya.manolova92@gmail.com'
START='2026-10-14T15:00:00+03:00'
STATE=ROOT/'artifacts/local-demo/secrets/phase14-live-session.json'

def main():
    state=json.loads((ROOT/'artifacts/phase14/demo-state.json').read_text())
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token'],'X-Tenant-ID':state['tenant_id']}
    policy=request(BASE,'/api/concierge/policy',staff)
    public_id=state['public_id']
    ticket=request(WIDGET,'/widget/admission/'+public_id,{'Origin':'http://127.0.0.1:5173'},{'locale':'bg-BG'})
    session=request(WIDGET,'/widget/redeem/'+public_id,{'Origin':WIDGET},{'ticket':ticket['ticket'],'parent_origin':'http://127.0.0.1:5173','locale':'bg-BG'})
    visitor={'Origin':WIDGET,'Authorization':'Bearer '+session['session_token']}
    availability=request(WIDGET,'/widget/v1/actions/'+public_id,visitor,{'tool':'ConciergeAvailability','arguments':{'day':'2026-10-14'},'event_id':'owner-live-availability-20261014','locale':'bg-BG'})
    # Inspect only slot presence; never disclose private busy periods.
    if START not in json.dumps(availability):
        print(json.dumps({'requested_time':START,'availability':'UNAVAILABLE','booking_created':False}));return
    try:
        request(BASE,'/api/concierge/policy',staff,{**policy,'operations_authorized':True},method='PUT')
        proof=request(WIDGET,'/widget/v1/verify-email/'+public_id,visitor,{'email':EMAIL,'locale':'bg-BG'})
        STATE.write_text(json.dumps({'public_id':public_id,'session_token':session['session_token'],'verification_id':proof['verification_id'],'starts_at':START,'email':EMAIL,'tenant_id':state['tenant_id']}))
        result='pending'
        for _ in range(15):
            jobs=request(BASE,'/api/concierge/email-jobs',staff)
            # The dedicated test tenant had no prior live email jobs.
            if jobs:
                result=jobs[-1]['status']
                if result not in ('pending','sending'):break
            time.sleep(2)
        print(json.dumps({'requested_time':START,'availability':'AVAILABLE','verification_email_status':result,'booking_created':False,'next_step':'Owner enters emailed verification code'}))
    finally:
        request(BASE,'/api/concierge/policy',staff,policy,method='PUT')

if __name__=='__main__':
    try:main()
    except Exception as error:
        print('Live test stopped: '+type(error).__name__)
        raise SystemExit(1) from None
