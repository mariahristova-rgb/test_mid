"""Read-only local API verification; never creates drafts, calls or appointments."""
import argparse
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import urllib.request
import urllib.error


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--require-idle',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[1]
    password=(root/'artifacts/local-demo/secrets/demo_login_password.txt').read_text(encoding='utf-8').strip()
    base='http://127.0.0.1:3017/backend'
    def send(path,headers=None,payload=None):
        body=json.dumps(payload).encode() if payload is not None else None
        request=urllib.request.Request(base+path,data=body,headers={**(headers or {}),'Content-Type':'application/json'})
        with urllib.request.urlopen(request,timeout=20) as response: return json.load(response)
    session=send('/api/demo/login',payload={'username':'demo','password':password})
    headers={'Authorization':'Bearer '+session['access_token'],'X-Tenant-ID':session['tenant_id']}
    bootstrap=send('/api/bootstrap',headers);calls=send('/api/calls',headers);bookings=send('/api/appointments',headers);assistants=send('/api/assistants',headers)
    def digest(value):return sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    projection=[]
    for assistant in assistants:
        voice=assistant['voice_settings']
        projection.append({'id':assistant['id'],'llm_provider':assistant['llm_provider'],'instructions':assistant['instructions'],
            'allowed_tools':assistant['allowed_tools'],'enabled_channels':assistant['enabled_channels'],
            'voice':{key:voice.get(key) for key in ('telephony_provider','stt_provider','tts_provider','voices','locale','recording','transcript_storage')},
            'confirmation_mode':voice.get('booking_confirmation_mode','speech')})
    active=sum(row['status'] not in ('ended','failed','transferred') for row in calls)
    report={'measured_at':datetime.now(timezone.utc).isoformat(),'tenant':session['tenant_id'],'login':'PASS',
        'role':bootstrap['user']['role'],'active_calls':active,'appointment_count':len(bookings),
        'appointment_state_hash':digest(sorted((row['id'],row['status'],row['starts_at'],row.get('conversation_id')) for row in bookings)),
        'assistant_configuration_hash':digest(projection),'test_studio_api':'not_available'}
    try:
        drafts=send('/api/ux/drafts',headers)
        report['test_studio_api']='PASS';report['saved_draft_count']=len(drafts)
    except urllib.error.HTTPError as error:
        if error.code !=404:raise
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    if args.require_idle and active: raise SystemExit('Local deployment blocked by active call')


if __name__=='__main__':main()
