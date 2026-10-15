"""Default-off Qwen3-8B benchmark using the existing QwenProvider stream protocol."""
import argparse
import json
import os
from pathlib import Path
import re
import statistics
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def capacity():
    return [{'customers':n,'conversations_per_day':50*n,'responses_per_day':50*n*6,
        'input_tokens_assumed':50*n*6*800,'output_tokens_assumed':50*n*6*200,
        'with_two_agent_calls_input_tokens_assumed':50*n*6*800*2,
        'peak_concurrency':'NOT_MEASURED','cost_per_customer':None} for n in (10,25,50,100)]


def benchmark(*,execute=False):
    report={'model':'Qwen3-8B','quantization':'AWQ','gpu_performance':'NOT_MEASURED',
        'production_ready':False,'capacity_assumptions':capacity(),'samples':[],
        'gpu_utilization':None,'queue_depth':None,'fairness':None,'cold_warm_start':'NOT_MEASURED'}
    if not execute:return report
    if os.getenv('PHASE26C_GPU_BENCHMARK_APPROVED')!='true' or not os.getenv('PHASE26C_GPU_APPROVAL_ID'):
        raise RuntimeError('Explicit GPU execution/cost approval required')
    revision=os.getenv('PHASE26C_MODEL_REVISION','');tokenizer=os.getenv('PHASE26C_TOKENIZER_REVISION','')
    runtime=os.getenv('PHASE26C_RUNTIME_IMAGE','')
    if not re.fullmatch('[0-9a-f]{40}',revision) or not re.fullmatch('[0-9a-f]{40}',tokenizer) or not re.fullmatch(r'.+@sha256:[0-9a-f]{64}',runtime):
        raise RuntimeError('Exact reviewed model/tokenizer/runtime revisions required')
    from semantic_os.backend.assistant.qwen import QwenProvider,QwenSettings
    from semantic_os.backend.assistant.self_hosted import deployment_secret
    from semantic_os.backend.agents.llm.provider import ChatMessage,GenerationRequest
    receipts=[]
    secret=deployment_secret('PHASE26C_QWEN_KEY')
    if not secret:raise RuntimeError('Approved private inference credential required')
    provider=QwenProvider(QwenSettings(endpoint=os.getenv('PHASE26C_QWEN_ENDPOINT',''),model_name='Qwen3-8B',
        served_model='Qwen3-8B',max_output_tokens=200,timeout_seconds=30),secret=secret,usage_sink=receipts.append)
    for locale,text in [('bg-BG','Как мога да запиша демонстрация?'),('en-US','How can I book a demonstration?')]:
        for context_repetitions in (1,8,16):
            request=GenerationRequest(messages=[ChatMessage('system','Answer briefly in '+locale+'. Synthetic context: '+'Approved demo information. '*context_repetitions),ChatMessage('user',text)],max_tokens=200)
            final=list(provider.stream(request))[-1]
            report['samples'].append({'locale':locale,'context_repetitions':context_repetitions,'metrics':final['metadata'],'input_tokens':receipts[-1]['prompt_tokens'],'output_tokens':receipts[-1]['completion_tokens']})
    report.update(model_revision=revision,tokenizer_revision=tokenizer,runtime_image=runtime,gpu_performance='INFERENCE_HTTP_MEASURED_GPU_TELEMETRY_UNVERIFIED')
    values=[sample['metrics']['elapsed_ms'] for sample in report['samples']]
    report['latency']={'p50_ms':statistics.median(values),'p95_ms':sorted(values)[-1],'sample_count':len(values),'p95_method':'small-sample conservative maximum'}
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--execute',action='store_true');args=parser.parse_args()
    report=benchmark(execute=args.execute)
    target=ROOT/'artifacts/phase26c/qwen-benchmark.json';target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
