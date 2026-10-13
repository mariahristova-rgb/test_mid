"""Synthetic SaaS projections, privacy and release-evidence tests; no live providers."""
from datetime import datetime, timedelta, timezone
import json
import unittest
from fastapi.testclient import TestClient
from semantic_os.backend.assistant.api import create_app
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.domain import Principal, DomainError
from semantic_os.backend.assistant.customer_workspace import CustomerWorkspace, Review, RequestChange, QualitySignal, OperationsTargets
from semantic_os.backend.assistant.inbox_queue import QueueChange
from semantic_os.backend.assistant.saas_domain import UsageEvent, Limit
from semantic_os.backend.assistant.saas_api import InvoiceAdjustment
from semantic_os.backend.assistant.ux import DraftInput, RunInput


class CustomerWorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.at=datetime.now(timezone.utc)
        self.app=create_app(store=self.store,demo_enabled=True,demo_token='workspace-offline-fixture',clock=lambda:self.at)
        self.service=self.app.state.customer_workspace
        self.actor=self.store.principal('demo-admin','demo')
        self.viewer=Principal('demo','viewer','viewer','viewer')
        self.operator=Principal('demo','operator','operator','operator')
    def tearDown(self):
        self.app.state.voice_runtime.shutdown();self.store.close()
    def draft(self):
        config={k:v for k,v in self.store.get('assistants','demo','default').items() if k not in ('id','tenant_id')}
        return self.app.state.ux.save(self.actor,DraftInput(config=config,business={'name':'Synthetic workspace'}))
    def test_health_is_tenant_scoped_and_excludes_customer_and_credential_content(self):
        self.store.add('operations_events','demo',{'kind':'google_connection','connection':'calendar','state':'connected','client_secret':'PRIVATE','refresh_token':'PRIVATE'})
        self.store.add('jobs','other',{'status':'failed','recipient':'private@example.invalid','subject':'PRIVATE'})
        health=self.service.health(self.viewer)
        self.assertEqual(health['unresolved_jobs'],0)
        self.assertEqual(health['connections'][0]['certification'],'NOT_CERTIFIED')
        self.assertNotIn('PRIVATE',json.dumps(health));self.assertFalse(health['assistants'][0]['voice_live_verified'])
    def test_default_runtime_clock_uses_existing_billing_clock(self):
        service=CustomerWorkspace(self.store,self.app.state.ux,self.app.state.billing,None)
        self.assertEqual(service.health(self.actor)['observed_at'],self.at.isoformat())
        self.assertEqual(service.purge(),0)

    def test_concierge_unknown_and_blocked_jobs_are_visible_without_private_content(self):
        owned=[]
        for status in ('delivery_unknown','blocked'):
            owned.append(self.store.add('jobs','demo',{'kind':'concierge_email','status':status,'recipient':'PRIVATE-recipient','subject':'PRIVATE-subject','attempts':1,'error_code':'delivery_unknown'}))
            self.store.add('jobs','other',{'kind':'concierge_email','status':status,'recipient':'OTHER-PRIVATE'})
        self.assertEqual(self.service.health(self.viewer)['unresolved_jobs'],2)
        quality=self.service.suggestions(self.operator)
        self.assertEqual(quality['groups'],{'delivery_uncertain':1,'provider_failure':1})
        headers={'Authorization':'Bearer workspace-offline-fixture','X-Tenant-ID':'demo'}
        client=TestClient(self.app)
        try:response=client.get('/api/operations',headers=headers)
        finally:client.close()
        self.assertEqual(response.status_code,200)
        report=response.json()
        self.assertEqual({j['id'] for j in report['failed_jobs']},{j['id'] for j in owned})
        self.assertNotIn('PRIVATE',json.dumps(report));self.assertNotIn('PRIVATE',json.dumps(quality))
    def test_progress_requires_admin_and_never_certifies_actual_installation(self):
        with self.assertRaises(DomainError):self.service.progress(self.viewer)
        draft=self.draft();progress=self.service.progress(self.actor)
        self.assertEqual(progress['drafts'][0]['id'],draft['id'])
        self.assertFalse(progress['complete']);self.assertEqual(progress['live_status'],'NOT_INDEPENDENTLY_VERIFIED')
        self.assertIn('required_tests_missing',progress['drafts'][0]['reasons'])
    def test_quality_review_is_tenant_bound_audited_and_cannot_mutate_assistant(self):
        original=self.store.get('assistants','demo','default')
        failure=self.store.add('jobs','demo',{'status':'uncertain','recipient':'PRIVATE','body':'PRIVATE'})
        self.store.add('jobs','other',{'status':'failed'})
        report=self.service.suggestions(self.operator)
        self.assertEqual(len(report['suggestions']),1)
        self.assertNotIn('PRIVATE',json.dumps(report))
        signal=report['suggestions'][0]
        self.assertEqual(signal['source_id'],failure['id'])
        with self.assertRaises(DomainError):self.service.review(self.viewer,signal['id'],Review(decision='accepted'))
        with self.assertRaises(DomainError):self.service.review(Principal('other','other','admin','other'),signal['id'],Review(decision='accepted'))
        result=self.service.review(self.operator,signal['id'],Review(decision='accepted'))
        self.assertFalse(result['live_mutation']);self.assertEqual(self.store.get('assistants','demo','default'),original)
        self.assertEqual(self.service.suggestions(self.operator)['suggestions'][0]['decision'],'accepted')
        self.assertTrue(any(r['action']=='quality:reviewed' for r in self.store.list('audit_events','demo')))
    def test_reported_quality_is_categorical_permission_bound_expiring_and_idempotent(self):
        conversation=self.store.add('conversations','demo',{'active_locale':'bg-BG','human_escalation':False})
        payload=QualitySignal(category='knowledge_gap',confirmed=True,event_id='reported-1')
        with self.assertRaises(DomainError):self.service.report_signal(self.viewer,conversation['id'],payload)
        with self.assertRaises(DomainError):self.service.report_signal(Principal('other','other','admin','other'),conversation['id'],payload)
        result=self.service.report_signal(self.operator,conversation['id'],payload)
        self.assertTrue(self.service.report_signal(self.operator,conversation['id'],payload)['duplicate'])
        with self.assertRaises(DomainError):self.service.report_signal(self.operator,conversation['id'],payload.model_copy(update={'category':'invalid_answer'}))
        report=self.service.suggestions(self.operator)
        self.assertEqual(report['suggestions'][0]['provenance'],'OPERATOR_REPORTED')
        self.assertEqual(report['suggestions'][0]['scenario'],'faq')
        self.assertFalse(self.store.get('conversations','demo',conversation['id'])['human_escalation'])
        self.store.update('operations_events','demo',result['id'],{'expires_at':(self.at-timedelta(seconds=1)).isoformat()})
        self.assertEqual(self.service.suggestions(self.operator)['suggestions'],[])
        self.assertEqual(self.service.purge(),1)
    def test_slo_targets_are_role_scoped_targets_not_observed_slas(self):
        payload=OperationsTargets(latency_p95_ms=1500,maximum_error_basis_points=100,availability_basis_points=9950,window_days=7)
        with self.assertRaises(DomainError):self.service.operations_targets(self.operator,payload)
        result=self.service.operations_targets(self.actor,payload)
        self.assertIsNone(result['error_budget_remaining'])
        self.assertEqual(result['evaluation'],'NOT_EVALUATED_REQUIRED_WINDOW_NOT_OBSERVED')
        other=Principal('other','other','admin','other')
        self.assertIsNone(self.service.operations_targets(other)['targets'])
    def test_usage_is_measured_deduplicated_and_costs_are_unavailable(self):
        event=UsageEvent(resource_id='synthetic',category='llm_input_tokens',quantity=42,unit='token',provider='self_hosted',timestamp=self.at,idempotency_key='tokens-1')
        ledger=self.app.state.billing.entitlements
        ledger.record('demo',event);ledger.record('demo',event)
        ledger.record('other',event.model_copy(update={'quantity':100}))
        usage=self.service.usage(self.viewer,self.at.strftime('%Y-%m'))
        self.assertEqual(usage['groups'][0]['quantity'],42)
        self.assertEqual(usage['costs']['compute_estimate'],'UNAVAILABLE')
        self.assertIsNone(usage['groups'][0]['assistant_id'])
    def test_quota_thresholds_are_deduplicated_per_period_and_hard_limit_stays_enforced(self):
        ledger=self.app.state.billing.entitlements
        ledger.plan=lambda _: {'id':'synthetic','version':1,'currency':'EUR','limits':{'ai_messages':Limit(maximum=100).model_dump()}}
        for identity,quantity in [('first',80),('second',15),('third',5)]:
            event=UsageEvent(resource_id='synthetic',category='ai_messages',quantity=quantity,unit='message',provider='mock',timestamp=self.at,idempotency_key=identity)
            ledger.record('demo',event);ledger.record('demo',event)
        self.assertEqual(sorted(w['threshold_percent'] for w in self.store.list('usage_warnings','demo')),[80,95,100])
        with self.assertRaises(DomainError):ledger.record('demo',UsageEvent(resource_id='synthetic',category='ai_messages',quantity=1,unit='message',provider='mock',timestamp=self.at,idempotency_key='overrun'))
    def test_stale_receipts_cannot_authorize_publish(self):
        draft=self.draft();ux=self.app.state.ux
        for locale in ('bg-BG','en-US'):
            for scenario in ('booking','rejection','ambiguous'):
                receipt=ux.test(self.actor,draft['id'],RunInput(revision=draft['revision'],scenario=scenario,locale=locale))
                self.store.update('operations_events','demo',receipt['id'],{'timestamp':(self.at-timedelta(days=8)).isoformat()})
        proof=ux.readiness(self.actor,draft)
        self.assertFalse(proof['can_publish']);self.assertIn('test_evidence_expired',proof['reasons'])
    def test_operational_counts_are_not_conversions_or_raw_tracking(self):
        self.store.add('conversations','demo',{'channel':'web_chat','active_locale':'bg-BG','content':'PRIVATE'})
        self.store.add('appointments','demo',{'status':'cancelled','name':'PRIVATE'})
        self.store.add('appointments','other',{'status':'confirmed'})
        report=self.service.analytics(self.viewer,30)
        self.assertNotIn('PRIVATE',json.dumps(report));self.assertEqual(report['appointments'],[{'status':'cancelled','quantity':1}])
        self.assertEqual(report['behavioral_tracking'],'OPTIONAL_EXPLICIT_CONSENT_ONLY');self.assertEqual(report['funnel'],[]);self.assertEqual(report['revenue'],'UNAVAILABLE')
    def test_requests_are_bounded_expired_excluded_and_pii_not_exposed(self):
        for status in ('fresh','expired'):
            self.store.add('operations_events','demo',{'kind':'concierge_request','action':'business','email':'PRIVATE','company':'PRIVATE','expires_at':(self.at+timedelta(days=1 if status=='fresh' else -1)).isoformat()})
        self.assertEqual(len(self.service.requests(self.viewer,25,0)['items']),1)
        self.assertNotIn('PRIVATE',json.dumps(self.service.requests(self.viewer,25,0)))
    def test_request_detail_is_explicit_audited_and_updates_are_cas_tenant_bound(self):
        row=self.store.add('operations_events','demo',{'kind':'concierge_request','email':'synthetic@example.invalid','status':'received','expires_at':(self.at+timedelta(days=1)).isoformat()})
        with self.assertRaises(DomainError):self.service.request_detail(self.viewer,row['id'])
        self.assertEqual(self.service.request_detail(self.operator,row['id'])['email'],'synthetic@example.invalid')
        result=self.service.request_change(self.actor,row['id'],RequestChange(revision=0,state='in_progress',assigned_user_id=self.actor.user_id))
        self.assertFalse(result['provider_message_sent'])
        with self.assertRaises(DomainError):self.service.request_change(self.actor,row['id'],RequestChange(revision=0,state='resolved'))
        foreign=self.store.list('users','other')[0]['id']
        with self.assertRaises(DomainError):self.service.request_change(self.actor,row['id'],RequestChange(revision=1,state='resolved',assigned_user_id=foreign))
        self.assertEqual(self.store.get('operations_events','demo',row['id'])['status'],'received')
    def test_queue_filters_apply_before_pagination_and_shared_unread_resets_on_new_inbound(self):
        old=self.store.add('conversations','demo',{'queue_priority':'urgent','operator_state':'assigned','queue_assigned_user_id':self.actor.user_id})
        self.store.add('conversations','demo',{'queue_priority':'normal'})
        self.store.add('messages','demo',{'conversation_id':old['id'],'direction':'inbound','timestamp':self.at.isoformat(),'content':'Synthetic'})
        items=self.store.inbox('demo',limit=1,filters={'queue_priority':'urgent'},unread=True)['items']
        self.assertEqual(items[0]['id'],old['id']);self.assertTrue(items[0]['queue_unread'])
        self.app.state.inbox_queue.change(self.actor,old['id'],QueueChange(revision=0,state='assigned',assigned_user_id=self.actor.user_id,mark_read=True))
        self.assertEqual(self.store.inbox('demo',limit=1,filters={'queue_priority':'urgent'},unread=True)['items'],[])
        self.store.add('messages','demo',{'conversation_id':old['id'],'direction':'inbound','timestamp':(self.at+timedelta(days=1)).isoformat(),'content':'Synthetic'})
        self.assertTrue(self.store.inbox('demo',limit=1,filters={'queue_priority':'urgent'},unread=True)['items'][0]['queue_unread'])
    def test_queue_priority_sla_and_resolution_preserve_ai_control(self):
        row=self.store.add('conversations','demo',{'status':'active','human_escalation':True})
        result=self.app.state.inbox_queue.change(self.operator,row['id'],QueueChange(revision=0,state='needs_review',priority='urgent',sla_minutes=30,mark_read=True))
        self.assertEqual(result['queue_priority'],'urgent');self.assertIsNotNone(result['queue_due_at'])
        result=self.app.state.inbox_queue.change(self.operator,row['id'],QueueChange(revision=1,state='resolved',resolution='answered'))
        self.assertEqual(result['queue_resolution'],'answered')
        self.assertTrue(self.store.get('conversations','demo',row['id'])['human_escalation'])
        with self.assertRaises(DomainError):self.app.state.inbox_queue.change(self.operator,row['id'],QueueChange(revision=2,state='assigned',assigned_user_id=self.operator.user_id,resolution='booked'))
    def test_http_validation_and_missing_authorization(self):
        client=TestClient(self.app)
        headers={'Authorization':'Bearer workspace-offline-fixture','X-Tenant-ID':'demo'}
        self.assertEqual(client.get('/api/workspace/health').status_code,401)
        self.assertEqual(client.get('/api/workspace/usage?period=2026-13',headers=headers).status_code,422)
        self.assertEqual(client.get('/api/workspace/requests?limit=101',headers=headers).status_code,422)
        self.assertEqual(client.get('/api/workspace/analytics?days=91',headers=headers).status_code,422)
        self.assertEqual(client.get('/api/workspace/health',headers=headers).status_code,200)
    def test_mock_invoice_adjustments_are_exact_append_only_and_capped(self):
        billing=self.app.state.billing
        invoice=self.store.add('billing_invoices','demo',{'provider':'mock','status':'paid','amount_minor':1234,'currency':'EUR'})
        payload=InvoiceAdjustment(amount_minor_text='234',kind='credit',reason='goodwill',event_id='credit-1',confirmed=True)
        record=billing.adjust_invoice(self.actor,invoice['id'],payload)
        self.assertFalse(record['provider_refund_sent'])
        self.assertTrue(billing.adjust_invoice(self.actor,invoice['id'],payload)['duplicate'])
        self.assertEqual(self.store.get('billing_invoices','demo',invoice['id']),invoice)
        with self.assertRaises(DomainError):self.store.update('operations_events','demo',record['id'],{'amount_minor_text':'1'})
        with self.assertRaises(DomainError):billing.adjust_invoice(self.actor,invoice['id'],payload.model_copy(update={'amount_minor_text':'235'}))
        with self.assertRaises(DomainError):billing.adjust_invoice(self.actor,invoice['id'],payload.model_copy(update={'amount_minor_text':'1001','event_id':'over-credit'}))
        with self.assertRaises(DomainError):billing.adjust_invoice(self.operator,invoice['id'],payload)
        with self.assertRaises(DomainError):billing.adjust_invoice(Principal('other','other','admin','other'),invoice['id'],payload)
        billing.adjust_invoice(self.actor,invoice['id'],payload.model_copy(update={'amount_minor_text':'1000','kind':'refund','event_id':'remaining'}))
        self.assertEqual(sum(int(r['amount_minor_text']) for r in billing.overview(self.actor)['adjustments']),1234)
        from semantic_os.backend.assistant.privacy import PrivacyRequest
        request=self.app.state.privacy.request(self.actor,PrivacyRequest(kind='tenant',confirmed=True))
        self.app.state.privacy.execute(self.actor,request['id'])
        self.assertEqual(len([r for r in self.store.list('operations_events','demo') if r.get('kind')=='billing_adjustment']),2)


if __name__=='__main__':unittest.main()
