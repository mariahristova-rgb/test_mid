"""Stage only the verified derived GGUF into a persistent project-owned Linux volume."""
import json
from pathlib import Path
import subprocess

ROOT=Path(__file__).resolve().parents[1]
VOLUME='testmid-cpu-voice_qwen-cache'
OWNER={'com.docker.compose.project':'testmid-cpu-voice','testmid.repository':'test_mid'}
EXPECTED='9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79'

CODE=r'''
import hashlib,json,os,pathlib,shutil,tempfile
root=pathlib.Path('/models')
target=root/'Qwen3-4B-Q4_K_M.gguf'
expected='9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79'
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''): value.update(chunk)
    return value.hexdigest()
if target.exists():
    if target.stat().st_size!=2497280800 or digest(target)!=expected:
        raise RuntimeError('Refusing to overwrite a different staged model')
else:
    source=pathlib.Path('/source/Qwen3-4B-Q4_K_M.gguf')
    if source.stat().st_size!=2497280800 or digest(source)!=expected:
        raise RuntimeError('Derived source checksum mismatch')
    with tempfile.NamedTemporaryFile(dir=root,prefix='staging-',delete=False) as output:
        temporary=pathlib.Path(output.name)
        with source.open('rb') as handle: shutil.copyfileobj(handle,output,1024*1024)
        output.flush(); os.fsync(output.fileno())
    if digest(temporary)!=expected: raise RuntimeError('Staged checksum mismatch')
    temporary.chmod(0o644)
    os.replace(temporary,target)
    (root/'source.json').write_text(json.dumps({'sha256':expected,'source':'verified derived Qwen3-4B Q4_K_M','originals_overwritten':False}))
print('Project-owned Linux model volume checksum verified; original cache is read-only.')
'''


def main():
    result=subprocess.run(['docker','volume','inspect','--format','{{json .Labels}}',VOLUME],capture_output=True,text=True)
    if result.returncode:
        command=['docker','volume','create']
        for key,value in OWNER.items(): command.extend(['--label',key+'='+value])
        subprocess.run([*command,VOLUME],check=True,capture_output=True)
    else:
        labels=json.loads(result.stdout) or {}
        if any(labels.get(key)!=value for key,value in OWNER.items()):
            raise RuntimeError('Refusing to adopt a volume without matching project ownership')
    source=ROOT/'.assistant-model-cache/converted/Qwen3-4B/hf-1cfa9a7208912126459214e8b04321603b3df60c'
    subprocess.run(['docker','run','--rm','--network','none','--memory','128m','--cpus','1',
        '--user','0:0','--entrypoint','python','-v',str(source)+':/source:ro','-v',VOLUME+':/models',
        'testmid-cpu-voice-backend:latest','-c',CODE],check=True)


if __name__=='__main__': main()
