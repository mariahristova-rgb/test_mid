"""Run the reviewed offline corpus; export categories/IDs only, never raw failures."""
import contextlib
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    source = ROOT / 'semantic_os/config/phase17_evaluations.json'
    raw = source.read_bytes()
    corpus = json.loads(raw)
    rows = []
    for case in corpus['cases']:
        started = time.perf_counter()
        # Test output/tracebacks can include fixture payloads; exclude from receipt.
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            suite = unittest.defaultTestLoader.loadTestsFromName('semantic_os.backend.tests.' + case['test'])
            result = unittest.TestResult()
            suite.run(result)
        status = 'PASS' if result.wasSuccessful() and result.testsRun == 1 and not result.skipped else 'FAIL'
        rows.append({'id':case['id'], 'category':case['category'], 'test':case['test'],
                     'status':status, 'tests_run':result.testsRun,
                     'elapsed_ms':round((time.perf_counter()-started)*1000, 3)})
    receipt = {'timestamp':datetime.now(timezone.utc).isoformat(), 'corpus_version':corpus['version'],
               'corpus_sha256':hashlib.sha256(raw).hexdigest(), 'scope':corpus['scope'],
               'cases':rows, 'unverified_layers':corpus['unverified_layers'],
               'promotion':'HUMAN_REVIEW_REQUIRED', 'pilot_ready':False}
    target = ROOT / 'artifacts/phase17/offline-evaluations.json'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'scope':corpus['scope'], 'passed':sum(r['status']=='PASS' for r in rows),
                      'total':len(rows), 'pilot_ready':False}))
    return int(any(row['status']!='PASS' for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
