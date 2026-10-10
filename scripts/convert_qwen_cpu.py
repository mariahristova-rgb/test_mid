"""Explicit separate GGUF conversion of verified existing artifacts; originals remain read-only."""
import argparse
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.model_artifacts import ModelCache, QwenManifest

IMAGE='ghcr.io/ggml-org/llama.cpp@sha256:25449b22adc2b5685e15032312ba5116cb67207bb424d5e321d00dc399882358'

def digest(path):
    value=sha256()
    with path.open('rb') as source:
        while chunk:=source.read(1024*1024): value.update(chunk)
    return value.hexdigest()

def main(args):
    root=Path(__file__).resolve().parents[1]
    source=args.source.resolve(); output=args.output.resolve(); logdir=root/'artifacts/model-conversion'
    if not source.is_relative_to(root/'.assistant-model-cache') or not output.is_relative_to(root/'.assistant-model-cache') or output==source:
        raise RuntimeError('Use distinct cache directories inside test_mid')
    marker=json.loads((source/'.verified.json').read_text())
    manifest=QwenManifest.model_validate(marker['manifest']); ModelCache.verify(source,manifest)
    if manifest.model_name!='Qwen3-4B' or manifest.format!='hf_safetensors': raise RuntimeError('Verified original Qwen3-4B Safetensors required')
    output.mkdir(parents=True,exist_ok=True); logdir.mkdir(parents=True,exist_ok=True)
    converted=output/'Qwen3-4B-BF16.gguf'; quantized=output/'Qwen3-4B-Q4_K_M.gguf'
    if (output/'conversion.json').exists():
        provenance=json.loads((output/'conversion.json').read_text())
        if digest(quantized)!=provenance['quantized_sha256']: raise RuntimeError('Converted cache checksum mismatch')
        print('Verified existing converted cache:',output); return
    mounts=['--mount','type=bind,source='+str(source)+',target=/source,readonly','--mount','type=bind,source='+str(output)+',target=/out']
    phases=[('bf16-conversion',['--entrypoint','python3',IMAGE,'/app/convert_hf_to_gguf.py','/source','--outtype','bf16','--use-temp-file','--outfile','/out/'+converted.name]),
        ('q4-quantization',['--entrypoint','/app/llama-quantize',IMAGE,'/out/'+converted.name,'/out/'+quantized.name,'Q4_K_M','4'])]
    for name, command in phases:
        target=converted if name=='bf16-conversion' else quantized
        if target.exists(): raise RuntimeError('Unverified partial conversion exists; inspect it before rerunning')
        print('Starting',name,'using the pinned official CPU tools',flush=True)
        with (logdir/(name+'.log')).open('wb') as log:
            result=subprocess.run(['docker','run','--rm','--cpus','4','--memory','4g',*mounts,*command],stdout=log,stderr=subprocess.STDOUT)
        if result.returncode: raise RuntimeError(name+' failed; inspect the redacted local conversion log')
        with target.open('rb') as source_file:
            if source_file.read(4)!=b'GGUF': raise RuntimeError('Invalid converted format')
        print(name,'completed:',target.stat().st_size,'bytes',flush=True)
    shutil.copyfile(source/'LICENSE',output/'LICENSE')
    provenance={'source_revision':manifest.version,'source_manifest':manifest.model_dump(mode='json'),'converter_image':IMAGE,
        'format':'GGUF','quantization':'Q4_K_M','intermediate':'BF16','originals_overwritten':False,
        'quantized_bytes':quantized.stat().st_size,'quantized_sha256':digest(quantized),'intermediate_sha256':digest(converted)}
    (output/'conversion.json').write_text(json.dumps(provenance,indent=2))
    print(json.dumps({key:provenance[key] for key in ('source_revision','quantization','quantized_bytes','quantized_sha256','originals_overwritten')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--source',type=Path,required=True); parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args())
