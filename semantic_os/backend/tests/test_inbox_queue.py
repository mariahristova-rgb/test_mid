import unittest
from datetime import datetime,timedelta,timezone
from semantic_os.backend.assistant.store import Store
from semantic_os.backend.assistant.domain import Principal,DomainError
from semantic_os.backend.assistant.inbox_queue import InboxQueue,QueueChange,InternalNote

class InboxQueueTests(unittest.TestCase):
    def setUp(self):
        self.store=Store();self.store.seed();self.store.seed('other','other')
        self.actor=self.store.principal('demo-admin','demo')
        self.service=InboxQueue(self.store)
        self.conversation=self.store.add('conversations','demo',{'assistant_id':'default','channel':'web_chat','status':'active','active_locale':'bg-BG','human_escalation':False})
    def tearDown(self):self.store.close()
    def test_assignment_is_tenant_bound_and_revision_conflicts_preserve_control(self):
        identity=self.conversation['id']
        result=self.service.change(self.actor,identity,QueueChange(revision=0,state='assigned',assigned_user_id=self.actor.user_id))
        self.assertEqual(result['queue_revision'],1)
        with self.assertRaises(DomainError):self.service.change(self.actor,identity,QueueChange(revision=0,state='resolved'))
        foreign=self.store.list('users','other')[0]['id']
        with self.assertRaises(DomainError):self.service.change(self.actor,identity,QueueChange(revision=1,state='assigned',assigned_user_id=foreign))
        row=self.store.get('conversations','demo',identity)
        self.assertEqual(row['operator_state'],'assigned');self.assertEqual(row['status'],'active');self.assertFalse(row['human_escalation'])
    def test_viewer_and_other_tenant_cannot_edit_or_read_notes(self):
        for actor in (Principal('demo','viewer','viewer','viewer'),Principal('other','operator','operator','operator')):
            with self.assertRaises(DomainError):self.service.change(actor,self.conversation['id'],QueueChange(revision=0,state='resolved'))
            with self.assertRaises(DomainError):self.service.notes(actor,self.conversation['id'],reveal=True)
    def test_notes_are_redacted_by_default_audited_when_revealed_and_expire(self):
        identity=self.conversation['id'];note=self.service.add_note(self.actor,identity,InternalNote(content='Synthetic follow-up only'))
        self.assertNotIn('content',self.service.notes(self.actor,identity)[0])
        self.assertEqual(self.service.notes(self.actor,identity,reveal=True)[0]['content'],'Synthetic follow-up only')
        self.assertTrue(any(r['action']=='inbox:notes_read' for r in self.store.list('audit_events','demo')))
        expiry=(datetime.now(timezone.utc)-timedelta(seconds=1)).isoformat()
        self.store.update('operations_events','demo',note['id'],{'expires_at':expiry})
        self.assertEqual(self.service.notes(self.actor,identity,reveal=True),[])
        self.assertEqual(self.service.purge(),1)
        self.assertEqual(self.store.get('operations_events','demo',note['id'])['content'],'')
    def test_blank_notes_and_assignment_without_member_are_rejected(self):
        with self.assertRaises(DomainError):self.service.add_note(self.actor,self.conversation['id'],InternalNote(content=' '))
        with self.assertRaises(DomainError):self.service.change(self.actor,self.conversation['id'],QueueChange(revision=0,state='assigned'))
    def test_existing_conversation_erasure_redacts_internal_notes(self):
        from types import SimpleNamespace
        from semantic_os.backend.assistant.privacy import PrivacyService
        note=self.service.add_note(self.actor,self.conversation['id'],InternalNote(content='Synthetic private note'))
        privacy=PrivacyService(self.store,SimpleNamespace(delete_content=lambda *_:None),lambda:datetime.now(timezone.utc))
        privacy.redact_conversation(self.actor,self.conversation['id'])
        self.assertEqual(self.service.notes(self.actor,self.conversation['id'],reveal=True),[])
        self.assertEqual(self.store.get('operations_events','demo',note['id'])['content'],'')
    def test_native_web_chat_operator_reply_has_human_provenance(self):
        from cryptography.fernet import Fernet
        from semantic_os.backend.assistant.api import create_app
        app=create_app(store=self.store,demo_enabled=True,demo_token='offline-queue-fixture',encryption_key=Fernet.generate_key().decode())
        try:
            app.state.messaging.human_control(self.actor,self.conversation['id'],'takeover')
            app.state.messaging.human_reply(self.actor,self.conversation['id'],'Synthetic staff reply','queue-provenance')
            messages=self.store.list('messages','demo',self.conversation['id'])
            self.assertEqual(messages[-1]['metadata']['kind'],'human')
            self.assertEqual(messages[-1]['metadata']['agent'],'human')
        finally:app.state.voice_runtime.shutdown()

if __name__=='__main__':unittest.main()
