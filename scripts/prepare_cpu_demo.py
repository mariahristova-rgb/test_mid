"""Create isolated local-demo configuration/secret references; never print credential values."""
from pathlib import Path
import json
import os
import secrets
import string
import subprocess
import sys
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from cryptography.fernet import Fernet
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.demo_seed import seed_smilecare, TENANT
from prepare_voice_demo import prepare

ROOT=Path(__file__).resolve().parents[1]
def main(neural=False):
    directory=ROOT/'artifacts/local-demo'; directory.mkdir(parents=True,exist_ok=True)
    keydir=directory/'secrets'; keydir.mkdir(exist_ok=True)
    if os.name=='nt':
        owner=os.environ.get('USERDOMAIN','')+'\\'+os.environ['USERNAME']
        result=subprocess.run(['icacls',str(keydir),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],capture_output=True)
        if result.returncode: raise RuntimeError('Private demo secret ACL configuration failed')
    for name in ('inference_key','speech_key','demo_token','ari_password','sip_password','encryption_key','demo_login_password'):
        path=keydir/(name+'.txt')
        if not path.exists():
            value=Fernet.generate_key().decode() if name=='encryption_key' else ''.join(secrets.choice(string.ascii_letters+string.digits) for _ in range(40))
            path.write_text(value); path.chmod(0o600)
    asterisk=directory/'asterisk'
    if not asterisk.exists():
        os.environ['ARI_PASSWORD']=(keydir/'ari_password.txt').read_text()
        os.environ['SIP_DEMO_PASSWORD']=(keydir/'sip_password.txt').read_text()
        prepare(asterisk)
    if os.name=='nt':
        result=subprocess.run(['icacls',str(asterisk),'/inheritance:r','/grant:r',owner+':(OI)(CI)F','*S-1-5-18:(OI)(CI)F','*S-1-5-32-544:(OI)(CI)F'],capture_output=True)
        if result.returncode: raise RuntimeError('Private SIP config ACL configuration failed')
    data=ROOT/'.assistant-data/cpu-voice-demo'; data.mkdir(parents=True,exist_ok=True)
    store=Store(str(data/'assistant.sqlite3'))
    seeded=seed_smilecare(store,mode='qwen',tts='espeak_ng')
    assistant=store.get('assistants',TENANT,'default')
    if assistant['llm_provider']!='qwen' or assistant['voice_settings']['tts_provider'] not in ('espeak_ng','bgtts38'): raise RuntimeError('Existing demo configuration differs; refusing to overwrite it')
    if any(row['status'] not in ('ended','failed','transferred') for row in store.list('call_sessions',TENANT)):
        raise RuntimeError('End all owned demo calls before changing voice configuration')
    if neural:
        from semantic_os.backend.assistant.speech_integrity import verify_bgtts_cache
        verify_bgtts_cache(ROOT/'.assistant-model-cache/bgtts38')
    voice={**assistant['voice_settings'],'tts_provider':'bgtts38' if neural else 'espeak_ng',
           'voices':{'bg-BG':'bgtts-bg','en-US':'bgtts-en'} if neural else {'bg-BG':'espeak-bg','en-US':'espeak-en'},
           'max_latency_ms':90000,'max_concurrent_calls':1}
    store.update('assistants',TENANT,'default',{'voice_settings':voice})
    store.close()
    converted=ROOT/'.assistant-model-cache/converted/Qwen3-4B/hf-1cfa9a7208912126459214e8b04321603b3df60c'
    whisper=ROOT/'.assistant-model-cache/speech/whisper-small/536b0662742c02347bc0e980a01041f333bce120'
    # Generic domain vocabulary only: no names, dates, expected utterances or consent overrides.
    worker=json.loads((whisper/'worker-config.json').read_text(encoding='utf-8'))
    worker['vocabulary']={'bg-BG':'Клиника, преглед, записване, час, свободен, потвърждавам, отменям.',
                          'en-US':'Clinic, checkup, appointment, availability, confirmation, cancellation.'}
    (whisper/'worker-config.json').write_text(json.dumps(worker,ensure_ascii=False,indent=2),encoding='utf-8')
    entries={'QWEN_GGUF_DIRECTORY':converted,'WHISPER_DIRECTORY':whisper,'VOICE_SECRET_DIRECTORY':keydir,'VOICE_DEMO_DATA':data,'ASTERISK_CONFIG_DIRECTORY':asterisk,'BG_TTS_DIRECTORY':ROOT/'.assistant-model-cache/bgtts38'}
    (directory/'compose.env').write_text(''.join(name+'='+str(path).replace('\\','/')+'\n' for name,path in entries.items())+'VOICE_UI_PORT=3011\n')
    print(json.dumps({'tenant_id':TENANT,'created':seeded['created'],'configuration':str(directory/'compose.env'),'credentials_printed':False}))

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--neural',action='store_true',help='Use the locally verified neural speech cache instead of the formant baseline')
    main(parser.parse_args().neural)
