"""Actual local-model measurements and bilingual protocol checks. No booking tool is executed."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sys
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.qwen import QwenProvider,QwenSettings
from semantic_os.backend.agents.llm.provider import ChatMessage,GenerationRequest
from semantic_os.backend.assistant.domain import BookingInterpretationRequest,DomainError
from semantic_os.backend.assistant.tools import SCHEMAS

ROOT=Path(__file__).resolve().parents[1]
def main(compact=False):
    if hasattr(sys.stdout,'reconfigure'): sys.stdout.reconfigure(encoding='utf-8')
    key=(ROOT/'artifacts/local-demo/secrets/inference_key.txt').read_text().strip()
    receipts=[]; results=[]
    provider=QwenProvider(QwenSettings(endpoint='http://127.0.0.1:8087/v1',allow_private_http=True,max_output_tokens=128,timeout_seconds=60,compact_intent=compact,compact_tools=compact),secret=key,usage_sink=receipts.append)
    for locale,greeting,booking in (('bg-BG','Здравейте!','Искам да запиша час за следващия понеделник в 15:00.'),
            ('en-US','Hello!','I would like to book an appointment next Monday at 3 PM.')):
        item={'locale':locale,'timestamp':datetime.now(timezone.utc).isoformat(),'source':'REAL_LOCAL_QWEN'}
        try:
            events=list(provider.stream(GenerationRequest(messages=[ChatMessage('system',f'Reply in {locale} in one short sentence.'),ChatMessage('user',greeting)],max_tokens=48)))
            item['reply']=''.join(event.get('text','') for event in events)
            item['stream_metrics']=events[-1]['metadata']
            intent=provider.interpret_booking(BookingInterpretationRequest(content=booking,locale=locale))
            item['intent']=intent.model_dump(mode='json')
            arguments={'starts_at':'2030-10-14T15:00:00+03:00','duration_minutes':30}
            proposed=provider.propose_tool('CheckAvailability',arguments,SCHEMAS['CheckAvailability'].model_json_schema())
            item['tool_arguments']=proposed
            item['tool_matches']=SCHEMAS['CheckAvailability'].model_validate(proposed).model_dump(mode='json')==SCHEMAS['CheckAvailability'].model_validate(arguments).model_dump(mode='json')
            item['passed']=intent.intent=='book' and item['tool_matches'] and '15:00' in (intent.date_text or '') and intent.duration_minutes in (None,30)
        except DomainError as exc: item.update(passed=False,error_code=exc.code)
        results.append(item)
        print(json.dumps(item,ensure_ascii=False),flush=True)
    report={'timestamp':datetime.now(timezone.utc).isoformat(),'model':'Qwen3-4B','quantization':'Q4_K_M','gpu_layers':0,'compact':compact,
        'results':results,'inference_receipts':receipts,'real_sip_calls_performed_by_this_script':0}
    target=ROOT/'artifacts/local-demo'/('llm-benchmark-compact.json' if compact else 'llm-benchmark.json'); target.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    archive=target.with_name(target.stem+'-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'.json')
    archive.write_bytes(target.read_bytes())
    return 0 if all(item['passed'] for item in results) else 1

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--compact',action='store_true')
    raise SystemExit(main(parser.parse_args().compact))
