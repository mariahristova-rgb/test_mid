"""Rehash the converted model before starting local inference; never alter source artifacts."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
DIRECTORY=ROOT/'.assistant-model-cache/converted/Qwen3-4B/hf-1cfa9a7208912126459214e8b04321603b3df60c'
EXPECTED='9a91506f18e56bfa9389a939db1b36029daf8c49327b0eb0bc9e19d627b00e79'


def main():
    provenance=json.loads((DIRECTORY/'conversion.json').read_text())
    target=DIRECTORY/'Qwen3-4B-Q4_K_M.gguf'
    if provenance.get('quantization')!='Q4_K_M' or provenance.get('originals_overwritten') is not False:
        raise RuntimeError('Unexpected conversion provenance')
    if provenance.get('quantized_sha256')!=EXPECTED or target.stat().st_size!=provenance['quantized_bytes']:
        raise RuntimeError('Converted artifact differs from reviewed conversion')
    digest=hashlib.sha256()
    with target.open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''): digest.update(chunk)
    if digest.hexdigest()!=EXPECTED: raise RuntimeError('Quantized model checksum mismatch')
    print('Reviewed Qwen3-4B Q4_K_M checksum verified; original files unchanged.')


if __name__=='__main__': main()
