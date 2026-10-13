"""Run the reviewed offline corpus; export categories/IDs only, never raw failures."""
import contextlib
import argparse
from datetime import datetime, timezone
import hashlib
import io
import json
import re
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
MODULES = {'test_assistant','test_google_concierge','test_concierge_api','test_customer_workspace','test_widget','test_booking_workflow','test_saas','test_ux','test_voice_integration'}
CATEGORIES = {'consent','tool','security','locale','provider','knowledge','recovery','ux'}


def validate_corpus(corpus):
    """A missing/empty/unsupported evaluation set must never certify success."""
    if not isinstance(corpus,dict) or set(corpus)!={'version','scope','cases','unverified_layers'}:
        raise ValueError('invalid_corpus')
    if not isinstance(corpus['version'],str) or not re.fullmatch(r'[0-9]+\.[0-9]+\.[0-9]+',corpus['version']) or corpus['scope']!='OFFLINE_CONTRACT_ONLY':
        raise ValueError('invalid_corpus')
    cases=corpus['cases'];layers=corpus['unverified_layers']
    if not isinstance(cases,list) or not 1<=len(cases)<=100 or not isinstance(layers,list) or not layers or any(not isinstance(v,str) or not re.fullmatch(r'[A-Z_]{1,80}',v) for v in layers):
        raise ValueError('invalid_corpus')
    ids=set();tests=set()
    for case in cases:
        if not isinstance(case,dict) or set(case)!={'id','category','test'}:raise ValueError('invalid_case')
        if not isinstance(case['id'],str) or not re.fullmatch(r'[a-z0-9-]{1,80}',case['id']) or not isinstance(case['category'],str) or case['category'] not in CATEGORIES or not isinstance(case['test'],str):raise ValueError('invalid_case')
        parts=case['test'].split('.')
        if len(parts)!=3 or parts[0] not in MODULES or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*',parts[1]) or not re.fullmatch(r'test_[a-z0-9_]+',parts[2]):raise ValueError('invalid_case')
        if case['id'] in ids or case['test'] in tests:raise ValueError('duplicate_case')
        ids.add(case['id']);tests.add(case['test'])
    return corpus


def evaluate(corpus,loader=None):
    validate_corpus(corpus)
    loader=loader or unittest.defaultTestLoader
    rows=[]
    for case in corpus['cases']:
        started=time.perf_counter()
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            suite=loader.loadTestsFromName('semantic_os.backend.tests.'+case['test'])
            result=unittest.TestResult();suite.run(result)
        status='PASS' if result.wasSuccessful() and result.testsRun==1 and not result.skipped else 'FAIL'
        rows.append({'id':case['id'],'category':case['category'],'test':case['test'],'status':status,
                     'tests_run':result.testsRun,'elapsed_ms':round((time.perf_counter()-started)*1000,3),
                     'measurement_scope':'SYNTHETIC_TEST_EXECUTION_INCLUDING_SETUP',
                     'token_usage':None,'token_usage_status':'NOT_MEASURED_MOCK_PROVIDER',
                     'failure_code':None if status=='PASS' else 'contract_failed_or_not_executed'})
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='artifacts/phase17/offline-evaluations.json')
    options=parser.parse_args()
    target=(ROOT/options.output).resolve()
    if not target.is_relative_to((ROOT/'artifacts').resolve()):
        print(json.dumps({'code':'invalid_receipt_target','pilot_ready':False}));return 1
    source = ROOT / 'semantic_os/config/phase17_evaluations.json'
    raw = source.read_bytes()
    try:corpus=validate_corpus(json.loads(raw))
    except (ValueError,TypeError):
        print(json.dumps({'scope':'OFFLINE_CONTRACT_ONLY','code':'invalid_corpus','pilot_ready':False}))
        return 1
    rows=evaluate(corpus)
    receipt = {'timestamp':datetime.now(timezone.utc).isoformat(), 'corpus_version':corpus['version'],
               'corpus_sha256':hashlib.sha256(raw).hexdigest(), 'scope':corpus['scope'],
               'cases':rows, 'unverified_layers':corpus['unverified_layers'],
               'promotion':'HUMAN_REVIEW_REQUIRED', 'pilot_ready':False}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'scope':corpus['scope'], 'passed':sum(r['status']=='PASS' for r in rows),
                      'total':len(rows), 'pilot_ready':False}))
    return int(any(row['status']!='PASS' for row in rows))


if __name__ == '__main__':
    raise SystemExit(main())
