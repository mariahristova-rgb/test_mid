"""Provision explicitly requested multilingual small STT; never fetches an LLM."""
import argparse
from contextlib import nullcontext
from hashlib import sha256
import json
from pathlib import Path
import urllib.request
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.local_speech import reviewed_artifact

REPO='Systran/faster-whisper-small'

def fetch(url, target=None):
    digest=sha256(); body=bytearray(); count=0
    try:
        with urllib.request.urlopen(url,timeout=60) as response:
            with target.open('wb') if target else nullcontext() as output:
                while chunk:=response.read(1024*1024):
                    count+=len(chunk)
                    if count>600_000_000: raise RuntimeError('Artifact size limit')
                    digest.update(chunk)
                    if output: output.write(chunk)
                    else: body.extend(chunk)
        return bytes(body),digest.hexdigest(),count
    except Exception: raise RuntimeError('Approved speech-source download failed') from None

def main(args):
    raw,_,_=fetch('https://huggingface.co/api/models/'+REPO+'?blobs=true')
    data=json.loads(raw); revision=data['sha']
    if data.get('cardData',{}).get('license')!='mit': raise RuntimeError('Speech model license review failed')
    root=args.cache.resolve()/'whisper-small'/revision
    manifest_path=root/'manifest.json'
    if root.exists():
        manifest=manifest_path.read_bytes(); digest=sha256(manifest).hexdigest()
        reviewed_artifact(root,manifest_path,digest,'stt')
        print(json.dumps({'root':str(root),'manifest':str(manifest_path),'sha256':digest,'downloaded':False})); return
    root.mkdir(parents=True)
    files=[]
    chosen={'README.md','config.json','model.bin','tokenizer.json','vocabulary.txt'}
    for item in data['siblings']:
        name=item['rfilename']
        if name not in chosen: continue
        _,digest,size=fetch('https://huggingface.co/'+REPO+'/resolve/'+revision+'/'+name,root/name)
        if size!=item['size'] or item.get('lfs',{}).get('sha256',digest)!=digest: raise RuntimeError('Speech artifact checksum mismatch')
        files.append({'path':name,'size_bytes':size,'sha256':digest})
        print('Verified STT artifact:',name,size,flush=True)
    license_data,digest,size=fetch('https://raw.githubusercontent.com/openai/whisper/main/LICENSE')
    if b'MIT License' not in license_data or b'Permission is hereby granted' not in license_data: raise RuntimeError('Original speech license unavailable')
    (root/'LICENSE').write_bytes(license_data); files.append({'path':'LICENSE','size_bytes':size,'sha256':digest})
    manifest={'kind':'stt','version':'hf-'+revision,'license_spdx':'MIT','license_reviewed':True,'locales':['bg-BG','en-US'],
        'source':'https://huggingface.co/'+REPO,'files':files}
    raw=json.dumps(manifest,indent=2).encode(); manifest_path.write_bytes(raw)
    digest=sha256(raw).hexdigest(); reviewed_artifact(root,manifest_path,digest,'stt')
    (root/'worker-config.json').write_text(json.dumps({'root':'/models','manifest':'/models/manifest.json','sha256':digest},indent=2))
    print(json.dumps({'root':str(root),'manifest':str(manifest_path),'sha256':digest,'downloaded':True}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--cache',type=Path,required=True)
    main(parser.parse_args())
