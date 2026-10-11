"""Tenant-owned operator metadata on the existing inbox, without external sends."""
from typing import Literal
from datetime import datetime,timedelta,timezone
import json
from fastapi import Depends
from pydantic import Field
from .domain import Contract, DomainError
from .store import now

class QueueChange(Contract):
    revision:int=Field(ge=0)
    state:Literal['needs_review','assigned','awaiting_customer','resolved']
    assigned_user_id:str|None=None
    priority:Literal['low','normal','high','urgent']|None=None
    sla_minutes:int|None=Field(default=None,ge=5,le=10080)
    resolution:Literal['answered','booked','cancelled','escalated','not_required']|None=None
    mark_read:bool=False

class InternalNote(Contract):
    content:str=Field(min_length=1,max_length=2000)

class InboxQueue:
    def __init__(self,store):self.store=store
    def notes(self,actor,identity,*,reveal=False):
        actor.require('approve');self.store.get('conversations',actor.tenant_id,identity)
        rows=[r for r in self.store.list('operations_events',actor.tenant_id,identity) if r.get('kind')=='operator_note' and not r.get('redacted') and r.get('expires_at','')>now()]
        if reveal:self.store.audit(actor,'inbox:notes_read',resource_id=identity)
        keys=('id','timestamp','author_id','content') if reveal else ('id','timestamp','author_id')
        return [{k:r.get(k) for k in keys} for r in rows[-100:]]
    def change(self,actor,identity,payload):
        actor.require('approve')
        with self.store.transaction():
            row=self.store.get('conversations',actor.tenant_id,identity)
            if row.get('queue_revision',0)!=payload.revision:raise DomainError('conflict',409)
            if payload.state=='assigned' and not payload.assigned_user_id:raise DomainError('invalid_input',422)
            if payload.assigned_user_id:
                member=self.store.get('users',actor.tenant_id,payload.assigned_user_id)
                if not member.get('enabled') or member['role'] not in ('admin','operator'):raise DomainError('forbidden',403)
            if payload.resolution and payload.state!='resolved':raise DomainError('invalid_input',422)
            changes={'operator_state':payload.state,'queue_assigned_user_id':payload.assigned_user_id,'queue_revision':payload.revision+1,'queue_updated_at':now()}
            if payload.priority is not None:changes['queue_priority']=payload.priority
            if payload.sla_minutes is not None:
                changes['queue_sla_minutes']=payload.sla_minutes
                changes['queue_due_at']=(datetime.now(timezone.utc)+timedelta(minutes=payload.sla_minutes)).isoformat()
            if payload.mark_read:changes['queue_read_at']=now()
            if payload.state=='resolved':changes.update(queue_resolved_at=now(),queue_resolution=payload.resolution or 'not_required')
            else:changes.update(queue_resolved_at=None,queue_resolution=None)
            result=self.store.update('conversations',actor.tenant_id,identity,changes)
            self.store.audit(actor,'inbox:queue_updated',resource_id=identity)
            return {k:result.get(k) for k in ('id','operator_state','queue_assigned_user_id','queue_revision','queue_updated_at','queue_priority','queue_due_at','queue_read_at','queue_resolution','queue_resolved_at')}
    def add_note(self,actor,identity,payload):
        actor.require('approve');self.store.get('conversations',actor.tenant_id,identity)
        content=payload.content.strip()
        if not content:raise DomainError('invalid_input',422)
        with self.store.transaction():
            if len(self.notes(actor,identity))>=100:raise DomainError('limit_reached',429)
            expiry=(datetime.now(timezone.utc)+timedelta(days=self.store.tenant(actor.tenant_id)['retention_days'])).isoformat()
            row=self.store.add('operations_events',actor.tenant_id,{'kind':'operator_note','conversation_id':identity,'content':content,'author_id':actor.user_id,'timestamp':now(),'expires_at':expiry})
            self.store.audit(actor,'inbox:note_added',resource_id=row['id'])
            return {'id':row['id'],'status':'saved'}
    def purge(self):
        with self.store.transaction():
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE json_extract(data,'$.kind')='operator_note' AND json_extract(data,'$.redacted') IS NULL AND json_extract(data,'$.expires_at')<=? LIMIT 500",(now(),)).fetchall()
            for item in rows:
                row=json.loads(item['data']);self.store.update('operations_events',row['tenant_id'],row['id'],{'content':'','redacted':True})
        return len(rows)

def register_inbox_queue(app,store,actor):
    service=InboxQueue(store)
    app.state.inbox_queue=service
    @app.put('/api/inbox/{identity}/queue')
    def change(identity:str,payload:QueueChange,principal=Depends(actor)):
        return service.change(principal,identity,payload)
    @app.get('/api/inbox/{identity}/notes')
    def notes(identity:str,reveal:bool=False,principal=Depends(actor)):
        return service.notes(principal,identity,reveal=reveal)
    @app.post('/api/inbox/{identity}/notes',status_code=201)
    def note(identity:str,payload:InternalNote,principal=Depends(actor)):
        return service.add_note(principal,identity,payload)
