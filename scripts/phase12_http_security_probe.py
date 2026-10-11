"""Probe a disposable widget integration inside the fictional demo tenant."""
import gzip
import json
from pathlib import Path
import urllib.request
import urllib.error
from phase12_local_journey import ROOT,BASE,WIDGET,SITE,STATE,request

def main():
    output=ROOT/'artifacts/phase12-http-security.json'
    if output.exists():raise SystemExit('Probe already recorded; review evidence before creating another integration.')
    state=json.loads(STATE.read_text())
    password=(ROOT/'artifacts/local-demo/secrets/demo_login_password.txt').read_text().strip()
    login=request(BASE,'/api/demo/login',data={'username':'demo','password':password})
    staff={'Authorization':'Bearer '+login['access_token'],'X-Tenant-ID':state['tenant_id']}
    existing=next(row for row in request(BASE,'/api/widgets',staff) if row['id']==state['integration_id'])
    row=request(BASE,'/api/widgets',staff,existing['settings']);identity=row['id'];public=row['public_id']
    proof=request(BASE,f'/api/widgets/{identity}/challenge',staff,{'origin':SITE})
    nonce=ROOT/'artifacts/phase12-site'/proof['path'].lstrip('/');nonce.parent.mkdir(parents=True,exist_ok=True);nonce.write_text(proof['content'],encoding='ascii')
    request(BASE,f'/api/widgets/{identity}/verify',staff,{'origin':SITE})
    request(BASE,f'/api/widgets/{identity}/publish',staff,{'draft_id':state['draft_id'],'confirmed':True})
    checks={'actual_domain_verification_on_corrected_network':True}
    def denied(name,base,path,headers,data=None,code=403):
        try:request(base,path,headers,data)
        except urllib.error.HTTPError as error:
            if error.code!=code:raise
            checks[name]=True
        else:raise RuntimeError(name+' unexpectedly succeeded')
    denied('unlisted_origin',WIDGET,'/widget/admission/'+public,{'Origin':'https://unlisted.example'}, {'locale':'auto'})
    denied('no_origin',WIDGET,'/widget/admission/'+public,{}, {'locale':'auto'})
    denied('staff_routes_absent_on_widget_proxy',WIDGET,'/api/bootstrap',{},code=404)
    ticket=request(WIDGET,'/widget/admission/'+public,{'Origin':SITE},{'locale':'auto'})
    payload={'ticket':ticket['ticket'],'parent_origin':SITE,'locale':'en-US'}
    session=request(WIDGET,'/widget/redeem/'+public,{'Origin':WIDGET},payload)
    bearer={'Authorization':'Bearer '+session['session_token'],'Origin':WIDGET}
    denied('one_use_ticket_replay',WIDGET,'/widget/redeem/'+public,{'Origin':WIDGET},payload)
    denied('visitor_cannot_read_private_assistants',BASE,'/api/assistants',{**bearer,'X-Tenant-ID':state['tenant_id']},code=401)
    denied('visitor_cannot_supply_tool',WIDGET,'/widget/messages/'+public,bearer,{'content':'Hello','event_id':'probe','tool':'SendMessage'},code=422)
    request(BASE,f'/api/widgets/{identity}/revoke',staff,{'confirmed':True})
    denied('revoke_blocks_admission',WIDGET,'/widget/admission/'+public,{'Origin':SITE},{'locale':'auto'})
    denied('revoke_blocks_existing_session',WIDGET,'/widget/messages/'+public,bearer,{'content':'Hello','event_id':'revoked'})
    checks['clear_after_revoke']=request(WIDGET,'/widget/clear/'+public,bearer,{'confirmed':True})['cleared']
    with urllib.request.urlopen(urllib.request.Request(WIDGET+'/widget/assets/v1.js',headers={'Accept-Encoding':'gzip'}),timeout=10) as response:
        body=response.read();checks['wire_gzip']=response.headers.get('Content-Encoding')=='gzip'
        if not checks['wire_gzip']:raise RuntimeError('Wire compression not enabled')
        checks['served_loader_matches_source']=gzip.decompress(body)==(ROOT/'semantic_os/widget/v1.js').read_bytes()
    with urllib.request.urlopen(SITE+'/',timeout=10) as response:
        page=response.read().decode();checks['sample_has_one_script']=page.count('<script ')==1
    if not all(checks.values()):raise RuntimeError('HTTP probe failed')
    output.write_text(json.dumps({'checks':checks,'scope':'Real HTTP, not browser rendering','probe_integration_id':identity,'status':'PASS'},indent=2))
    print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
