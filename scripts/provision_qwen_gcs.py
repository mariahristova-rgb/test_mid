"""Pin and verify the owner's existing GCS model. No uploads or registry fallback."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.model_artifacts import ModelCache


class ExistingGCloud:
    def __init__(self, bucket, prefix):
        if not re.fullmatch(r'[a-z0-9_.-]+',bucket) or not re.fullmatch(r'[A-Za-z0-9_./-]+',prefix) or '..' in prefix.split('/'):
            raise ValueError('Invalid explicit GCS source')
        self.base='gs://'+bucket+'/'+prefix.strip('/')+'/'
        self.executable=shutil.which('gcloud.cmd') or shutil.which('gcloud')
        if not self.executable: raise RuntimeError('Existing Google Cloud CLI authentication is required')

    def command(self, *args):
        result=subprocess.run([self.executable,'storage',*args],capture_output=True)
        if result.returncode: raise RuntimeError('Read-only GCS operation failed; inspect the CLI authentication separately')
        return result.stdout

    def describe(self, name):
        return json.loads(self.command('objects','describe',self.base+name,'--format=json(name,size,generation,md5_hash,crc32c_hash)'))

    def download(self, file, target):
        result=subprocess.run([self.executable,'storage','cp',self.base+file.path+'#'+str(file.generation),str(target),'--quiet'])
        if result.returncode: raise RuntimeError('Pinned artifact download failed')


def provision(args):
    source=ExistingGCloud(args.bucket,args.prefix)
    names=('LICENSE','README.md','config.json','generation_config.json','merges.txt','model.safetensors.index.json',
        'tokenizer.json','tokenizer_config.json','vocab.json','model-00001-of-00003.safetensors',
        'model-00002-of-00003.safetensors','model-00003-of-00003.safetensors')
    def inspect(name):
        metadata=source.describe(name)
        if metadata['name'] != args.prefix.strip('/')+'/'+name: raise RuntimeError('Unexpected object source')
        cache_metadata=source.command('cat',source.base+'.cache/huggingface/download/'+name+'.metadata').decode().splitlines()
        revision, etag=cache_metadata[:2]
        if not re.fullmatch('[a-f0-9]{40}',revision): raise RuntimeError('Unverified revision')
        if name.endswith('.safetensors'):
            if not re.fullmatch('[a-f0-9]{64}',etag): raise RuntimeError('Missing original LFS SHA-256')
            digest=etag
        else:
            raw=source.command('cat',source.base+name+'#'+str(metadata['generation']))
            if len(raw)>20_000_000: raise RuntimeError('Metadata size limit exceeded')
            digest=sha256(raw).hexdigest()
            if name=='LICENSE' and b'Apache License' not in raw: raise RuntimeError('License review required')
        print('Verified metadata:',name,flush=True)
        return revision, {'path':name,'sha256':digest,'size_bytes':int(metadata['size']),'generation':int(metadata['generation'])},metadata
    with ThreadPoolExecutor(max_workers=4) as pool: entries=list(pool.map(inspect,names))
    revisions={entry[0] for entry in entries}
    if len(revisions)!=1: raise RuntimeError('Model/tokenizer revisions differ')
    manifest={'model_name':'Qwen3-4B','version':'hf-'+next(iter(revisions)), 'format':'hf_safetensors',
        'license_spdx':'Apache-2.0','license_reviewed':True,'files':[entry[1] for entry in entries]}
    directory=args.manifest_directory.resolve(); directory.mkdir(parents=True,exist_ok=True)
    raw=json.dumps(manifest,indent=2).encode(); digest=sha256(raw).hexdigest()
    target=directory/'qwen3-4b-gcs-manifest.json'
    if target.exists() and target.read_bytes()!=raw: raise RuntimeError('Refusing to replace a different pinned manifest')
    target.write_bytes(raw)
    (directory/'qwen3-4b-gcs-manifest.sha256').write_text(digest+'\n')
    (directory/'qwen3-4b-gcs-objects.json').write_text(json.dumps({'source':source.base,'revision':next(iter(revisions)),
        'objects':[entry[2] for entry in entries], 'weights_downloaded':False},indent=2))
    print('Pinned revision:',next(iter(revisions)), 'manifest SHA-256:',digest,flush=True)
    if args.download:
        parsed=ModelCache.manifest(raw,digest)
        result=ModelCache(args.cache).sync(parsed,source)
        audit=directory/'qwen3-4b-gcs-objects.json'
        verified=json.loads(audit.read_text())
        verified.update(weights_downloaded=True,verified_cache=result['cache'])
        audit.write_text(json.dumps(verified,indent=2))
        print(json.dumps(result),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bucket',required=True)
    parser.add_argument('--prefix',required=True)
    parser.add_argument('--manifest-directory',type=Path,required=True)
    parser.add_argument('--cache',type=Path,required=True)
    parser.add_argument('--download',action='store_true',help='Download only this existing pinned model into the local cache')
    provision(parser.parse_args())
