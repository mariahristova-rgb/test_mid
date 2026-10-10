"""Actual serial Windows SIP journeys using synthetic audio, never injected transcripts."""
from datetime import datetime, timezone
from datetime import timedelta
from zoneinfo import ZoneInfo
import json
from pathlib import Path
import httpx
import subprocess
import threading
import time
import uuid
import wave
import struct
import shutil
import hashlib

ROOT=Path(__file__).resolve().parents[1]
TENANT='smilecare-demo'


def rows(table):
    if table not in ('tenants','call_sessions','conversations','appointments','agent_executions','tool_executions'):
        raise ValueError('Invalid evidence table')
    paths={'tenants':'bootstrap','call_sessions':'calls','conversations':'conversations','appointments':'appointments'}
    if table not in paths: raise ValueError('Use call-scoped activity for execution evidence')
    value=api(paths[table])
    return [value['tenant']] if table=='tenants' else value


def api(path):
    token=(ROOT/'artifacts/local-demo/secrets/demo_token.txt').read_text().strip()
    with httpx.Client(timeout=110,trust_env=False,follow_redirects=False) as client:
        response=client.get('http://127.0.0.1:3011/backend/api/'+path,
            headers={'Authorization':'Bearer '+token,'X-Tenant-ID':TENANT})
        response.raise_for_status()
        return response.json()


def attempt(locale, late=False, *, audio_directory=None, expected_contact=None, evidence_directory=None, explicit_locale=False, expected_hour=None, audio_source='BG38_NEURAL_CPU_ADAPTER'):
    from semantic_os.backend.assistant.demo_seed import MARKER
    if not any(row.get('demo_marker')==MARKER for row in rows('tenants')):
        raise RuntimeError('Only the marked fictional demo is allowed')
    identifier=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'-'+uuid.uuid4().hex[:6]
    requested_hour = expected_hour if expected_hour is not None else (16 if late else 15)
    if not isinstance(requested_hour, int) or not 0 <= requested_hour < 24: raise ValueError('Invalid intended hour')
    out=(Path(evidence_directory) if evidence_directory else ROOT/'artifacts/local-demo/sip-tests')/identifier
    if not out.resolve().is_relative_to(ROOT/'artifacts'): raise RuntimeError('Evidence must remain in repository artifacts')
    out.mkdir(parents=True)
    secret=(ROOT/'artifacts/local-demo/secrets/sip_password.txt').read_text().strip()
    private=ROOT/'artifacts/local-demo/secrets'/('journey-'+identifier+'.conf')
    audio_root=Path(audio_directory) if audio_directory else ROOT/'artifacts/neural-voice-audio/call-input'
    files=[audio_root/f'{locale}-{phase}.wav'
           for phase in ('request-late' if late else 'request','name','confirm')]
    input_dir=out/'inputs'; input_dir.mkdir()
    input_hashes={}
    for path in files:
        shutil.copyfile(path,input_dir/path.name)
        input_hashes[path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
    before={row['id'] for row in rows('call_sessions')}
    options=['--id=sip:1001@127.0.0.1:5060','--registrar=sip:127.0.0.1:5060','--realm=*',
        '--username=1001','--password='+secret,'--local-port=15061','--ip-addr=127.0.0.1',
        '--bound-addr=127.0.0.1','--no-tcp','--null-audio','--no-vad','--clock-rate=8000',
        '--max-calls=1','--rtp-port=40000','--log-level=3','--app-log-level=3',
        '--rec-file='+str(out/'received.wav'),'--auto-rec']
    options.extend('--play-file='+str(path) for path in files)
    private.write_text('\n'.join(options)+'\n')
    process=subprocess.Popen([str(ROOT/'artifacts/sip-client/pjsua-x86_64-w64-mingw32.exe'),
        '--config-file='+str(private),'sip:2000@127.0.0.1:5060'],stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace')
    logs=[]; samples=[]; stopped=threading.Event()
    def collect():
        for line in process.stdout:
            if secret not in line and not any(word in line.casefold() for word in ('authorization:','password','nonce=')):
                logs.append(line.rstrip())
    def sample():
        while not stopped.is_set():
            try:
                result=subprocess.run(['docker','stats','--no-stream','--format','{{json .}}',
                    *['testmid-cpu-voice-'+name+'-1' for name in ('qwen','stt','tts','backend','asterisk')]],
                    capture_output=True,text=True,timeout=15)
                samples.append({'at':datetime.now(timezone.utc).isoformat(),'exit_code':result.returncode,
                    'samples':[json.loads(line) for line in result.stdout.splitlines() if line.startswith('{')]})
            except (subprocess.TimeoutExpired,ValueError) as exc:
                samples.append({'at':datetime.now(timezone.utc).isoformat(),'error':type(exc).__name__})
            stopped.wait(2)
    reader=threading.Thread(target=collect,daemon=True); reader.start()
    sampler=threading.Thread(target=sample,daemon=True); sampler.start()
    report={'attempt_id':identifier,'locale':locale,'timestamp':datetime.now(timezone.utc).isoformat(),
        'audio_source':'BG38_NEURAL_CPU_ADAPTER','input_sha256':input_hashes,'passed':False,'phases':[],'booking_ids':[]}
    started=time.monotonic(); call=None
    def command(value):
        process.stdin.write(value+'\n'); process.stdin.flush()
    try:
        command('cl')
        time.sleep(18)  # Allow the warm greeting; actual receipt is checked after the call.
        calls=[row for row in rows('call_sessions') if row['id'] not in before]
        if len(calls)!=1: raise RuntimeError(f'Exactly one actual new SIP session required; observed {len(calls)}')
        call=calls[0]; report['call_id']=call['id']; report['conversation_id']=call['conversation_id']
        if explicit_locale:
            token=(ROOT/'artifacts/local-demo/secrets/demo_token.txt').read_text().strip()
            with httpx.Client(timeout=30,trust_env=False) as client:
                response=client.post('http://127.0.0.1:3011/backend/api/calls/'+call['id']+'/events',
                    headers={'Authorization':'Bearer '+token,'X-Tenant-ID':TENANT},
                    json={'action':'language','locale':locale,'event_id':'explicit-test-locale-'+identifier})
                response.raise_for_status()
            report['locale_selection_source']='authenticated existing call-language control; no transcript injection'
        reference=datetime.fromisoformat(call['started_at']).astimezone(ZoneInfo('Europe/Sofia'))
        expected_day=reference.date()+timedelta(days=(0-reference.weekday())%7 or 7)
        expected_name=expected_contact or ('Мария Демо' if locale=='bg-BG' else 'Jane Smith')
        for number,(phase,target,path) in enumerate(zip(('request','name','confirm'),
                ('need_name','awaiting_confirmation','completed'),files),1):
            phase_start=time.monotonic()
            output_before=api('operations')['metrics'].get('utterance_final_to_first_output_packet',{}).get('count',0)
            # Official PJSUA layout: master 0, three players 1..3, recorder 4, ring 5..6, call 7.
            command(f'cc\n{number}\n7')
            with wave.open(str(path)) as wav: duration=wav.getnframes()/wav.getframerate()
            time.sleep(max(.02,duration-.5))  # Disconnect within the verified trailing silence, before WAV looping.
            command(f'cd\n{number}\n7')
            observed=None
            while time.monotonic()-phase_start<100:
                conversations=[row for row in rows('conversations') if row['id']==call['conversation_id']]
                observed=(conversations[0].get('booking_state') or {}) if conversations else {}
                if observed.get('status')==target: break
                current=[row for row in rows('call_sessions') if row['id']==call['id']][0]
                if current['status'] in ('ended','failed','transferred'): break
                time.sleep(1)
            report['phases'].append({'phase':phase,'wall_ms':(time.monotonic()-phase_start)*1000,
                'expected_status':target,'actual_state':observed})
            if observed.get('status')!=target: break
            if target=='awaiting_confirmation':
                proposed=datetime.fromisoformat(observed['starts_at']).astimezone(ZoneInfo('Europe/Sofia'))
                matches=(observed.get('contact_name','').casefold()==expected_name.casefold()
                    and proposed.date()==expected_day and proposed.hour==requested_hour
                    and proposed.minute==0 and observed.get('duration_minutes')==30)
                report['phases'][-1]['proposed_details_match_expected']=matches
                if not matches:
                    report['confirmation_withheld']='Proposed details differ from the intended caller details'
                    break
            # Wait for actual business-response RTP emission; an acknowledgement alone is insufficient.
            emitted=False
            while time.monotonic()-phase_start<100:
                if api('operations')['metrics'].get('utterance_final_to_first_output_packet',{}).get('count',0)>output_before:
                    emitted=True; break
                current=[row for row in rows('call_sessions') if row['id']==call['id']][0]
                if current['status'] in ('ended','failed','transferred'): break
                time.sleep(1)
            report['phases'][-1]['business_response_first_packet_observed']=emitted
            if not emitted: break
            time.sleep(10)  # Bounded short spoken response must reach the recording before the next utterance.
        bookings=[row for row in rows('appointments') if row.get('conversation_id')==call['conversation_id'] and row.get('status')=='confirmed']
        report['booking_ids']=[row['id'] for row in bookings]
        report['expected_booking']={'date':str(expected_day),'hour':requested_hour,'duration_minutes':30,'contact_name':expected_name}
        report['golden_booking_matches']=len(bookings)==1 and all(
            datetime.fromisoformat(row['starts_at']).astimezone(ZoneInfo('Europe/Sofia')).date()==expected_day
            and datetime.fromisoformat(row['starts_at']).astimezone(ZoneInfo('Europe/Sofia')).hour==requested_hour
            and row['duration_minutes']==30 and row['contact_name'].casefold()==expected_name.casefold() for row in bookings)
        report['passed']=len(report['phases'])==3 and report['phases'][-1]['actual_state'].get('status')=='completed' and report['golden_booking_matches'] and all(p.get('business_response_first_packet_observed') for p in report['phases'])
    except Exception as exc:
        report['error']=type(exc).__name__+': '+str(exc)
    finally:
        if process.poll() is None:
            command('cl\nq')
            try: process.wait(timeout=15)
            except subprocess.TimeoutExpired: process.kill(); process.wait()
        reader.join(timeout=2); stopped.set(); sampler.join(timeout=17)
        report['wall_ms']=(time.monotonic()-started)*1000
        report['client_exit_code']=process.returncode
        report['registration_observed']=any('registration success' in line and 'status=200' in line for line in logs)
        report['confirmed_observed']=any('state changed to CONFIRMED' in line for line in logs)
        report['expected_call_port_observed']=any('Port #07' in line and 'sip:2000' in line for line in logs)
        report['passed']=report['passed'] and report['expected_call_port_observed'] and report['confirmed_observed']
        report['business_workflow_passed']=report['passed']
        report['caller_heard_confirmation_verified']=False
        report['passed']=False  # Human intelligibility/caller-heard confirmation cannot be inferred from a booking row.
        if call:
            activity=api('calls/'+call['id']+'/activity')
            report['final_call']=activity['call']
            report['agents']=activity['agents']
            report['tools']=activity['tools']
        report['first_audible_latency_ms']=None
        report['audio_source']=audio_source
        report['operations_snapshot']=api('operations')
        if (out/'received.wav').exists():
            with wave.open(str(out/'received.wav')) as wav:
                rate=wav.getframerate(); audio=wav.readframes(wav.getnframes())
            pcm=struct.unpack('<'+'h'*(len(audio)//2),audio)
            report['received_audio']={'seconds':len(pcm)/rate,'nonzero_samples':sum(value!=0 for value in pcm),
                'peak_amplitude':max(map(abs,pcm),default=0),
                'recording_first_nonsilent_offset_ms':next((index*1000/rate for index,value in enumerate(pcm) if value!=0),None)}
        (out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        (out/'resources.json').write_text(json.dumps(samples,indent=2))
        (out/'client-redacted.log').write_text('\n'.join(logs),encoding='utf-8')
    print(json.dumps({key:report.get(key) for key in ('attempt_id','locale','passed','call_id','booking_ids','error')},ensure_ascii=False),flush=True)
    return report


if __name__=='__main__':
    import sys
    sys.path.insert(0,str(ROOT))
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    results=[attempt(locale,late=index==2) for index,locale in enumerate(('bg-BG','en-US','bg-BG'))]
    (ROOT/'artifacts/local-demo/three-call-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    raise SystemExit(0 if all(row['passed'] for row in results) else 1)
