"""Owner-attended synthetic SIP exercise; preserved receipts never imply human acceptance."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_cpu_voice_calls import ROOT, attempt


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--tester-available',action='store_true')
    parser.add_argument('--first-only',action='store_true')
    parser.add_argument('--continue-sequence',action='store_true')
    args=parser.parse_args()
    if not args.tester_available: raise RuntimeError('Phase 8B requires an available authorized tester')
    evidence=ROOT/'artifacts/phase8b'
    regression=(evidence/'confirmation-regression.txt').read_text(encoding='utf-8')
    if not regression.rstrip().endswith('OK'): raise RuntimeError('Deterministic confirmation regressions must pass first')
    summary=evidence/'three-call-results.json'
    results=json.loads(summary.read_text(encoding='utf-8')) if args.continue_sequence else []
    if args.continue_sequence and (len(results)!=1 or not results[0].get('business_workflow_passed')):
        raise RuntimeError('The preceding Bulgarian business journey must pass before continuing its streak')
    plan=[('bg-BG',False,16),('en-US',False,15),('bg-BG',True,17)]
    selected=plan[1:] if args.continue_sequence else plan[:1] if args.first_only else plan
    for locale,late,hour in selected:
        result=attempt(locale,late=late,audio_directory=evidence/'call-input',
            expected_contact='Мария Иванова' if locale=='bg-BG' else 'Jane Smith',
            evidence_directory=evidence/'sip-tests',explicit_locale=True,expected_hour=hour,
            audio_source='authorized synthetic BG38 request/name + Windows Ivan BG confirmation/17h; response TTS remains BG38')
        result['authorized_tester_declared_available']=True
        results.append(result)
        summary.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
        if not result.get('business_workflow_passed'): break
    return 0 if all(row.get('business_workflow_passed') for row in results) else 1


if __name__=='__main__': raise SystemExit(main())
