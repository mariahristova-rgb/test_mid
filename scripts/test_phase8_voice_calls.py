"""Actual BG/EN/BG SIP attempts with existing controls, recorded as failures when gates fail."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_cpu_voice_calls import attempt,ROOT


def main():
    folder=ROOT/'artifacts/phase8/call-input'
    results=[]
    for index,locale in enumerate(('bg-BG','en-US','bg-BG')):
        result=attempt(locale,late=index==2,audio_directory=folder,
            expected_contact='Мария Иванова' if locale=='bg-BG' else 'Jane Smith',
            evidence_directory=ROOT/'artifacts/phase8/sip-tests',explicit_locale=True)
        results.append(result)
        (ROOT/'artifacts/phase8/three-call-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(row['passed'] for row in results) else 1


if __name__=='__main__': raise SystemExit(main())
