"""Isolated preparation safety; these fixtures do not certify a live release."""
from datetime import datetime, timezone
from pathlib import Path
import os
import subprocess
import unittest
from semantic_os.backend.assistant.calendar import MockCalendarProvider
from semantic_os.backend.assistant.demo_seed import seed_smilecare, reset_smilecare, TENANT
from semantic_os.backend.assistant.domain import DomainError
from semantic_os.backend.assistant.store import Store
from scripts.demo_readiness import acceptance_gate


class DemoResetTests(unittest.TestCase):
    def test_repeat_reset_preserves_seed_other_tenant_and_audit(self):
        store=Store()
        try:
            seed_smilecare(store,mode='mock',clock=lambda:datetime(2030,10,8,tzinfo=timezone.utc))
            store.seed('other','other-admin')
            conv=store.add('conversations',TENANT,{'assistant_id':'default','active_locale':'bg-BG','status':'open'})
            appointment=MockCalendarProvider(store).create(TENANT,{'starts_at':'2030-10-14T15:00:00+03:00','duration_minutes':30,'contact_name':'Fictional Demo'},conv,'Europe/Sofia')
            actor=store.principal('smilecare-demo-admin',TENANT)
            for _ in range(2): reset_smilecare(store,actor)
            rows=store.list('appointments',TENANT)
            self.assertEqual(len(rows),3)
            self.assertEqual(store.get('appointments',TENANT,appointment['id'])['status'],'cancelled')
            self.assertEqual(sum(r['status']=='confirmed' and r.get('seeded_fixture') for r in rows),2)
            self.assertEqual(store.get('conversations',TENANT,conv['id'])['status'],'closed')
            self.assertEqual(store.get('assistants','other','default')['name'],'Assistant')
            self.assertFalse(seed_smilecare(store)['created'])
            self.assertTrue(store.list('audit_events',TENANT))
        finally:store.close()


class ReadinessGateTests(unittest.TestCase):
    def rows(self):
        return [{'business_workflow_passed':True,'golden_booking_matches':True,'booking_ids':[str(n)]} for n in range(3)]

    def test_business_and_health_cannot_waive_human_gates(self):
        blockers=acceptance_gate(self.rows(),[{'case':'reject','decision_if_pending':'reject'}])
        self.assertTrue(any('Human-heard' in b for b in blockers))
        self.assertTrue(any('dashboard' in b for b in blockers))

    def test_question_false_positive_blocks_even_human_verified_calls(self):
        rows=[{**r,'caller_heard_confirmation_verified':True,'dashboard_verified':True} for r in self.rows()]
        self.assertTrue(acceptance_gate(rows,[{'case':'question','decision_if_pending':'confirm'}]))

    def test_missing_or_duplicate_evidence_fails_closed(self):
        self.assertTrue(acceptance_gate([],[]))
        rows=self.rows();rows[2]['booking_ids']=rows[0]['booking_ids']
        self.assertTrue(any('Distinct' in b for b in acceptance_gate(rows,[])))

    def test_incomplete_controls_cannot_certify_acoustic_safety(self):
        rows=[{**r,'caller_heard_confirmation_verified':True,'dashboard_verified':True} for r in self.rows()]
        blockers=acceptance_gate(rows,[{'case':'reject','decision_if_pending':'reject'}])
        self.assertTrue(any('recognition safety' in b for b in blockers))

    def test_missing_sip_teardown_cannot_pass_business_receipt(self):
        self.assertTrue(any('termination' in b for b in acceptance_gate(self.rows(),[])))

    @unittest.skipUnless(os.name=='nt','Windows maintenance wrapper')
    def test_docker_diagnostic_failure_blocks_real_reset_wrapper(self):
        root=Path(__file__).resolve().parents[3]
        script=str(root/'scripts/demo/reset-demo.ps1').replace("'","''")
        # Execute the actual wrapper with a failed, output-free Docker command.
        # It must throw before launching Python/SQLite maintenance.
        code="function docker { $global:LASTEXITCODE=1 }; try { & '"+script+"' -Confirm; exit 9 } catch { if ($_.Exception.Message -like 'Cannot verify the demo is stopped*') { Write-Output 'blocked-before-database'; exit 0 }; throw }"
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',code],capture_output=True,text=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('blocked-before-database',result.stdout)

    def test_active_call_prevents_reset_without_archiving(self):
        store=Store()
        try:
            seed_smilecare(store,mode='mock')
            store.add('call_sessions',TENANT,{'status':'listening'})
            with self.assertRaises(DomainError):reset_smilecare(store,store.principal('smilecare-demo-admin',TENANT))
            self.assertTrue(all(r['status']=='confirmed' for r in store.list('appointments',TENANT)))
        finally:store.close()
