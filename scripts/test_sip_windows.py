"""Actual Windows PJSUA registration/control harness. Record only observed outcomes."""
import argparse
from ipaddress import ip_address
from datetime import datetime,timezone
import json
from pathlib import Path
import queue
import subprocess
import threading
import time

ROOT=Path(__file__).resolve().parents[1]
def main(args):
    address=ip_address(args.media_host)
    if not address.is_private or address.is_unspecified or address.is_link_local: raise RuntimeError('Use only a verified private local media interface')
    directory=ROOT/'artifacts/local-demo/sip-tests'; directory.mkdir(parents=True,exist_ok=True)
    secret=(ROOT/'artifacts/local-demo/secrets/sip_password.txt').read_text().strip()
    config=ROOT/'artifacts/local-demo/secrets/pjsua-test.conf'
    options=['--id=sip:1001@127.0.0.1:5060','--registrar=sip:127.0.0.1:5060','--realm=*',
        '--username=1001','--password='+secret,'--local-port=15061','--ip-addr='+args.media_host,'--bound-addr=127.0.0.1','--no-tcp',
        '--null-audio','--no-vad','--clock-rate=8000','--max-calls=1','--rtp-port=40000','--log-level=3','--app-log-level=3']
    if args.call: options+=['--rec-file='+str(directory/'received-greeting.wav'),'--auto-rec']
    if args.play: options+=['--play-file='+str(args.play.resolve())]
    config.write_text('\n'.join(options)+'\n')
    exe=ROOT/'artifacts/sip-client/pjsua-x86_64-w64-mingw32.exe'
    command=[str(exe),'--config-file='+str(config)]
    if args.call: command.append('sip:2000@127.0.0.1:5060')
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
        text=True,encoding='utf-8',errors='replace',bufsize=1)
    messages=queue.Queue(); observed=[]
    def collect():
        for line in process.stdout:
            if secret in line or any(word in line.casefold() for word in ('authorization:','password','nonce=')): continue
            messages.put(line.rstrip())
    reader=threading.Thread(target=collect,daemon=True); reader.start()
    start=time.monotonic(); registered=False
    try:
        if args.play:
            time.sleep(2)
            # With one WAV player and one recorder: player=1, recorder=2, call slot=5.
            process.stdin.write('cl\ncc\n1\n5\n'); process.stdin.flush()
        while time.monotonic()-start<25 and process.poll() is None:
            try: line=messages.get(timeout=.5)
            except queue.Empty: continue
            observed.append(line)
            if ('registration success' in line.casefold() or 'registration complete' in line.casefold()) and ('200' in line or 'success' in line.casefold()):
                registered=True
                if not args.call: break
        if registered:
            process.stdin.write('cl\n'); process.stdin.flush(); time.sleep(1)
        process.stdin.write('q\n'); process.stdin.flush()
        try: process.wait(timeout=10)
        except subprocess.TimeoutExpired: process.kill(); process.wait()
        reader.join(timeout=1)
        while not messages.empty(): observed.append(messages.get())
        registered=registered or any('registration success' in line.casefold() and 'status=200' in line.casefold() for line in observed)
    finally:
        if process.poll() is None: process.kill(); process.wait()
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'client':'Official PJSUA 2.17 Windows cross-build','target':'127.0.0.1:5060',
        'extension':'1001','registration_observed':registered,'sip_call_requested':args.call,'booking_journeys_completed':0,
        'client_exit_code':process.returncode,'observed_log':observed}
    (directory/('call-establishment.json' if args.call else 'registration.json')).write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({key:report[key] for key in report if key!='observed_log'}))
    print('\n'.join(observed[-12:]))
    return 0 if registered else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--call',action='store_true',help='Actually dial private extension 2000 and capture only synthetic demo greeting audio')
    parser.add_argument('--play',type=Path,help='Transmit this generated synthetic test WAV through the actual softphone media bridge')
    parser.add_argument('--media-host',default='127.0.0.1',help='Verified private WSL host interface for SDP/RTP; never a public bind address')
    raise SystemExit(main(parser.parse_args()))
