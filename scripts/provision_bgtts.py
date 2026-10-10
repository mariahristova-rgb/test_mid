"""Provision the reviewed small BG/EN TTS and MIT codec; never fetches an LLM."""
from hashlib import sha256
import json
from pathlib import Path
import sys
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from provision_speech import fetch

ROOT=Path(__file__).resolve().parents[1]
MODELS=(('beleata74/BgTTS-38M-V2','3f6ca06b3ca78352eb00d8e96349c0bedaa3d2f1','apache-2.0',
    {'checkpoint_inference.pt','README.md','samples/sample_female_bg1.wav'}),
    ('Aratako/MioCodec-25Hz-24kHz','3a737f0de2c6324cb2fe40c1fbd1056c7add423d','mit',{'model.safetensors','config.yaml','README.md'}))

def main():
    base=ROOT/'.assistant-model-cache/bgtts38'; base.mkdir(parents=True,exist_ok=True)
    all_records=[]
    for repo,revision,license,files in MODELS:
        raw,_,_=fetch('https://huggingface.co/api/models/'+repo+'?blobs=true')
        metadata=json.loads(raw)
        if metadata['sha']!=revision or metadata.get('cardData',{}).get('license')!=license: raise RuntimeError('Explicit TTS revision/license changed')
        target=base/('tts' if 'BgTTS' in repo else 'codec'); target.mkdir(exist_ok=True)
        for item in metadata['siblings']:
            name=item['rfilename']
            if name not in files: continue
            path=target/name; path.parent.mkdir(parents=True,exist_ok=True)
            expected=item.get('lfs',{}).get('sha256')
            if path.exists() and path.stat().st_size==item['size']:
                digest=sha256(path.read_bytes()).hexdigest()
                if expected and digest!=expected: raise RuntimeError('Existing TTS checksum mismatch')
                size=path.stat().st_size
            else:
                _,digest,size=fetch('https://huggingface.co/'+repo+'/resolve/'+revision+'/'+name,path)
            if size!=item['size'] or expected and digest!=expected: raise RuntimeError('TTS checksum mismatch')
            all_records.append({'repo':repo,'revision':revision,'license_declared':license,'path':str(path.relative_to(base)), 'size_bytes':size,'sha256':digest})
            print('Verified neural speech asset:',repo,name,size,flush=True)
    (base/'provenance.json').write_text(json.dumps({'models':all_records,'voice_reference':'publisher-generated synthetic sample; no real person is targeted',
        'pickle_loading':'weights_only=True required','gpu_required':False,'runtime_acceptance':'NOT_YET_TESTED'},indent=2))
    feature=base/'torch-cache/hub/checkpoints/wavlm_base_plus.pth'
    feature.parent.mkdir(parents=True,exist_ok=True)
    if not feature.exists():
        _,digest,size=fetch('https://download.pytorch.org/torchaudio/models/wavlm_base_plus.pth',feature)
        (base/'wavlm-source.json').write_text(json.dumps({'source':'https://download.pytorch.org/torchaudio/models/wavlm_base_plus.pth','sha256':digest,'size_bytes':size,'task':'speech features, not an LLM'},indent=2))

if __name__=='__main__': main()
