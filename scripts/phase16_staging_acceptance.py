"""HTTPS protocol acceptance for the named synthetic staging only; no browser claim."""
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import httpx

ROOT=Path(__file__).resolve().parents[1]
SITE='https://assistant-demo.ontelyx.tech'
WIDGET='https://assistant-staging.ontelyx.tech'
ADMIN='https://assistant-admin-staging.ontelyx.tech'

def main():
    approved=json.loads((ROOT/'semantic_os/config/ontelyx_concierge.json').read_text(encoding='utf-8'))['faq_entries'][0]
    result={'timestamp':datetime.now(timezone.utc).isoformat(),'scope':'HTTPS_PROTOCOL_SYNTHETIC_FAQ_NOT_BROWSER_ACCEPTANCE','checks':[]}
    with httpx.Client(timeout=20,follow_redirects=False) as client:
        response=client.get(SITE+'/');response.raise_for_status()
        match=re.search(r'data-assistant-id="(wdg_[a-f0-9]{32})"',response.text)
        if not match:raise RuntimeError('Published public identifier missing')
        identifier=match.group(1)
        for locale,key in [('bg-BG','bg'),('en-US','en')]:
            response=client.post(WIDGET+'/widget/admission/'+identifier,headers={'Origin':SITE},json={'locale':locale})
            response.raise_for_status();ticket=response.json()['ticket']
            response=client.post(WIDGET+'/widget/redeem/'+identifier,headers={'Origin':WIDGET},json={'ticket':ticket,'parent_origin':SITE,'locale':locale})
            response.raise_for_status();token=response.json()['session_token']
            headers={'Origin':WIDGET,'Authorization':'Bearer '+token}
            payload={'content':approved['question_'+key],'locale':locale,'event_id':'phase16-approved-faq-'+key}
            response=client.post(WIDGET+'/widget/messages/'+identifier,headers=headers,json=payload)
            response.raise_for_status();answer=response.json()
            if answer['locale']!=locale or approved['answer_'+key] not in answer['response']:raise RuntimeError('Approved language/answer check failed')
            repeated=client.post(WIDGET+'/widget/messages/'+identifier,headers=headers,json=payload)
            repeated.raise_for_status()
            if not repeated.json().get('duplicate'):raise RuntimeError('Duplicate prevention failed')
            result['checks'].append({'locale':locale,'approved_faq':'PASS','duplicate':'PASS','scope':'MOCK_KNOWLEDGE_ONLY'})
            response=client.post(WIDGET+'/widget/clear/'+identifier,headers=headers,json={'confirmed':True})
            response.raise_for_status()
            result['checks'][-1]['chat_cleared']='PASS'
        for host,path,expected in [(ADMIN,'/backend/health/ready',200),(ADMIN,'/backend/api/bootstrap',401),(WIDGET,'/api/bootstrap',404),(SITE,'/public-state.json',404)]:
            response=client.get(host+path)
            if response.status_code!=expected:raise RuntimeError('Readiness/private boundary check failed')
            result['checks'].append({'path':host+path,'status':response.status_code,'tls_verified':True})
    (ROOT/'artifacts/phase16/https-acceptance.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
