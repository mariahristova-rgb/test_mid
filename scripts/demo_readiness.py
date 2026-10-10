"""Read-only local-demo audit. Process health cannot certify spoken/UI acceptance."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROOT=Path(__file__).resolve().parents[1]
PROJECT='testmid-cpu-voice'


def command(args):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True,timeout=25)
    if result.returncode:raise RuntimeError('Local command failed; inspect the named component')
    return result.stdout


def acceptance_gate(results,matrix):
    blockers=[]
    if len(results)!=3 or not all(r.get('business_workflow_passed') and r.get('golden_booking_matches') for r in results):
        blockers.append('Three consecutive exact SIP business journeys are missing')
    if not results or not all(r.get('caller_heard_confirmation_verified') for r in results):
        blockers.append('Human-heard Bulgarian and English confirmations remain unverified')
    if not results or not all(r.get('dashboard_verified') for r in results):
        blockers.append('Actual dashboard call/conversation/agent/tool/booking visibility remains unverified')
    required_controls={'negative','reject','ambiguous','question'}
    if not required_controls <= {r.get('case') for r in matrix} or any(r.get('case') in required_controls and r.get('decision_if_pending')=='confirm' for r in matrix):
        blockers.append('Telephone-band ambiguity/negative/question recognition safety has not passed')
    if not results or not all(r.get('registration_observed') and r.get('confirmed_observed') and r.get('client_exit_code')==0 and r.get('final_call',{}).get('status')=='ended' for r in results):
        blockers.append('Registered SIP establishment and clean call termination evidence is missing')
    ids=[i for r in results for i in r.get('booking_ids',[])]
    if len(ids)!=3 or len(set(ids))!=3:blockers.append('Distinct one-per-call booking evidence is missing')
    return blockers


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'artifacts/phase9/readiness.json')
    args=parser.parse_args()
    target=args.output.resolve()
    if not target.is_relative_to(ROOT/'artifacts'):parser.error('Audit output must remain in test_mid/artifacts')
    report={'verified_at':datetime.now(timezone.utc).isoformat(),'project':PROJECT,'decision':'DEMO_BLOCKED',
        'scope':'isolated preparation; no release certification, call, reset or external notification','components':[],'blockers':[]}
    def check(name,action,remedy):
        try:
            state,evidence=action()
            report['components'].append({'component':name,'status':state,'evidence':evidence,'remaining_action':remedy})
            if state=='BLOCKED':report['blockers'].append(name+': '+remedy)
        except Exception as exc:
            report['components'].append({'component':name,'status':'BLOCKED','code':type(exc).__name__,'remaining_action':remedy})
            report['blockers'].append(name+': '+remedy)
    def container(service):
        value=json.loads(command(['docker','inspect','--format','{{json .}}',PROJECT+'-'+service+'-1']))
        # Never serialize Config.Env, command arguments, mounts or secret values.
        if value['Config'].get('Labels',{}).get('com.docker.compose.project')!=PROJECT:raise RuntimeError('Unexpected container ownership')
        state=value['State'];health=state.get('Health',{}).get('Status')
        level='HEALTHY' if state['Running'] and health=='healthy' else 'RUNNING' if state['Running'] else 'BLOCKED'
        return level,{'image_reference':value['Config']['Image'],'image_id':value['Image'],
            'running':state['Running'],'health':health,'oom_killed':state['OOMKilled'],'restart_count':value['RestartCount']}
    for service in ('asterisk','qwen','stt','tts','backend','frontend'):
        check('docker_'+service,lambda service=service:container(service),'Inspect only this project; restart the affected idle service using the documented Compose files')
    def local_health(service,port,path):
        snippet=f"import json,urllib.request;print(json.dumps(json.load(urllib.request.urlopen('http://127.0.0.1:{port}{path}',timeout=8))))"
        value=json.loads(command(['docker','exec',PROJECT+'-'+service+'-1','python','-c',snippet]))
        return 'HEALTHY',value
    check('stt',lambda:local_health('stt',8000,'/health'),'Restore the existing single STT worker; do not download a new model')
    check('tts',lambda:local_health('tts',8000,'/health'),'Restore the existing BG38 worker; no automatic Ivan replacement')
    def qwen():
        with urllib.request.urlopen('http://127.0.0.1:8087/health',timeout=8) as response:value=json.load(response)
        return 'HEALTHY',value
    check('qwen',qwen,'Check the pinned model volume and CPU/memory pressure; health alone does not measure inference')
    def dashboard():
        with urllib.request.urlopen('http://127.0.0.1:3011/dashboard',timeout=8) as response:code=response.status
        return ('HEALTHY' if code==200 else 'BLOCKED'),{'http_status':code,'url':'http://127.0.0.1:3011/dashboard','visual_verification':False}
    check('dashboard_http',dashboard,'Use port 3011 locally; owner must inspect actual persisted rows')
    def sip():
        value=command(['docker','exec',PROJECT+'-asterisk-1','asterisk','-rx','pjsip show endpoint 1001'])
        valid='Endpoint:' in value and '1001' in value
        return ('HEALTHY' if valid else 'BLOCKED'),{'endpoint_1001_configured':valid,'new_registration_test':False,'pstn_verified':False}
    check('sip_registration_capability',sip,'Inspect PJSIP endpoint 1001 and authorized softphone; do not imply PSTN support')
    def db():
        snippet="import sqlite3,json;c=sqlite3.connect('file:/data/assistant.sqlite3?mode=ro',uri=True);print(json.dumps({'integrity':c.execute('pragma integrity_check').fetchone()[0],'foreign_key_errors':len(c.execute('pragma foreign_key_check').fetchall()),'migration_version':c.execute('select max(version) from schema_migrations').fetchone()[0]}))"
        value=json.loads(command(['docker','exec',PROJECT+'-backend-1','python','-c',snippet]))
        return ('VERIFIED' if value=={'integrity':'ok','foreign_key_errors':0,'migration_version':5} else 'BLOCKED'),value
    check('database',db,'Keep the single SQLite writer; use authenticated backup/restore, never replace a live database')
    try:
        from test_cpu_voice_calls import api
        bootstrap=api('bootstrap');tenant=bootstrap['tenant'];assistant=next(a for a in api('assistants') if a['id']=='default')
        def tenant_config():
            from semantic_os.backend.assistant.demo_seed import MARKER
            policy=tenant.get('calendar_policy',{})
            valid=tenant.get('demo_marker')==MARKER and tenant.get('timezone')=='Europe/Sofia' and tenant.get('default_locale')=='bg-BG' and len(policy.get('resources',[]))==2 and policy.get('weekdays')==[0,1,2,3,4] and policy.get('opens')=='09:00' and policy.get('closes')=='18:00' and policy.get('duration_minutes')==30
            return ('VERIFIED' if valid else 'BLOCKED'),{'tenant_id':tenant['id'],'synthetic_marker_matches':tenant.get('demo_marker')==MARKER,'timezone':tenant.get('timezone'),'dentists':len(policy.get('resources',[])),'calendar_provider':'MOCK_ONLY'}
        check('demo_tenant',tenant_config,'Review the marked fictional tenant; do not adopt or reset any other tenant')
        check('agents_tools',lambda:('VERIFIED' if set(assistant['assigned_agents'])=={'receptionist','executor'} and {'CheckAvailability','CreateAppointment'}<=set(assistant['allowed_tools']) else 'BLOCKED',{'agents':assistant['assigned_agents'],'booking_tools_configured':{'CheckAvailability','CreateAppointment'}<=set(assistant['allowed_tools'])}),'Enable both existing agents and authorized booking tools in the demo configuration')
        ops=api('operations')
        check('voice_gateway',lambda:('HEALTHY' if ops['worker'].get('ari_status')=='connected_unverified' else 'BLOCKED',{'ari_status':ops['worker'].get('ari_status')}),'Inspect the existing ARI bridge and scoped Asterisk/backend logs')
        channels=set(assistant['enabled_channels'])
        check('voice_webchat_config',lambda:('VERIFIED' if {'voice','web_chat'}<=channels and assistant['voice_settings']['max_concurrent_calls']==1 else 'BLOCKED',{'enabled_channels':sorted(channels),'voice_locale_default':assistant['voice_settings']['default_locale'] if 'default_locale' in assistant['voice_settings'] else assistant['default_locale'],'concurrent_calls':assistant['voice_settings']['max_concurrent_calls']}),'Keep UI, conversation and voice locales separate; max one demo call')
        def fixed_slots():
            from semantic_os.backend.assistant.calendar import MockCalendarProvider
            bookings=api('appointments')
            class ReadOnlyCalendarView:
                def tenant(self,owner):
                    if owner!=tenant['id']:raise ValueError('Unexpected tenant')
                    return tenant
                def list(self,table,owner):
                    if table!='appointments' or owner!=tenant['id']:raise ValueError('Unexpected scope')
                    return bookings
            calendar=MockCalendarProvider(ReadOnlyCalendarView())
            plan=json.loads((ROOT/'docs/demo/demo-plan.json').read_text(encoding='utf-8'))
            slots=[{'starts_at':row['starts_at'],'available_resources':len(calendar.available_resources(tenant['id'],row['starts_at'],plan['duration_minutes'])),'future':datetime.fromisoformat(row['starts_at'])>datetime.now(timezone.utc)} for row in plan['planned_slots']]
            return ('VERIFIED' if all(row['future'] and row['available_resources'] for row in slots) else 'BLOCKED'),{'calendar':'MOCK_ONLY','slots':slots,'reservations_created':False}
        check('fixed_demo_slots',fixed_slots,'Review the fixed dated plan, verify availability and rehearse after the Phase 8B gate passes; never silently change its date')
        report['notification_connections']=[{'channel':r['channel'],'provider':r['provider'],'configured_state':r.get('state'),'classification':'MOCK_ONLY' if r['provider']=='mock' else 'NOT_CONFIGURED' if not r.get('enabled') else 'BLOCKED'} for r in api('messaging/connections')]
    except Exception as exc:
        report['blockers'].append('Authenticated demo API audit failed: '+type(exc).__name__)
    try:
        evidence=json.loads((ROOT/'artifacts/phase8b/three-call-results.json').read_text(encoding='utf-8'))
        matrix=json.loads((ROOT/'artifacts/phase8b/stt-matrix.json').read_text(encoding='utf-8'))['results']
        report['blockers'].extend(acceptance_gate(evidence,matrix))
    except Exception:report['blockers'].append('Required Phase 8B acceptance evidence is missing or invalid')
    git_head=subprocess.run(['git','rev-parse','--verify','HEAD'],cwd=ROOT,capture_output=True,text=True)
    report['git_commit']=git_head.stdout.strip() if git_head.returncode==0 else None
    report['release_candidate_id']=None
    if report['git_commit'] is None:report['blockers'].append('Git has no commit; the working tree cannot be identified as a committed release candidate')
    report['decision']='DEMO_BLOCKED' if report['blockers'] else 'PREPARATION_HEALTHY_UNCERTIFIED'
    target.parent.mkdir(parents=True,exist_ok=True);target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    return 2 if report['blockers'] else 0


if __name__=='__main__':raise SystemExit(main())
