"""Content-free SaaS projections over the existing tenant store; no provider writes."""
from datetime import datetime, timedelta, timezone
from collections import Counter
import json
import calendar
from typing import Literal
from fastapi import Depends, Query
from pydantic import Field
from .domain import Contract, DomainError
from .store import event_key, now


class Review(Contract):
    decision: Literal['accepted', 'dismissed']

class RequestChange(Contract):
    revision:int=Field(ge=0)
    state:Literal['received','in_progress','resolved']
    assigned_user_id:str|None=None

class QualitySignal(Contract):
    category:Literal['stt_uncertainty','ambiguous_consent','tool_denial','provider_outage','knowledge_gap','invalid_answer','duplicate_action','abandonment']
    confirmed:Literal[True]
    event_id:str=Field(min_length=1,max_length=100)

class OperationsTargets(Contract):
    latency_p95_ms:int=Field(ge=50,le=120000)
    maximum_error_basis_points:int=Field(ge=0,le=10000)
    availability_basis_points:int=Field(ge=5000,le=10000)
    window_days:int=Field(ge=1,le=30)


class CustomerWorkspace:
    def __init__(self, store, ux, billing, clock):
        self.store, self.ux, self.billing = store, ux, billing
        self.clock = clock or billing.clock

    def rows(self, tenant, table, *, kind=None, limit=1000):
        if table not in {'operations_events', 'jobs', 'tool_executions', 'conversations', 'appointments'}:
            raise ValueError('Unknown projection source')
        condition = " AND json_extract(data,'$.kind')=?" if kind else ''
        args = (tenant, kind, limit+1) if kind else (tenant, limit+1)
        with self.store.lock:
            result = [json.loads(row['data']) for row in self.store.db.execute(
                f'SELECT data FROM {table} WHERE tenant_id=?{condition} ORDER BY created_at DESC,id DESC LIMIT ?', args)]
        return result[:limit], len(result)>limit

    def progress(self, actor):
        actor.require('configure')
        tenant = self.store.tenant(actor.tenant_id)
        drafts, truncated = self.rows(actor.tenant_id, 'operations_events', kind='ux_draft', limit=100)
        widgets, widget_truncated = self.rows(actor.tenant_id, 'operations_events', kind='widget_integration', limit=100)
        editable = [d for d in drafts if d.get('status')=='draft']
        ready = []
        for draft in editable:
            proof = self.ux.readiness(actor, draft)
            ready.append({'id':draft['id'],'name':draft['config']['name'],'step':draft['step'],
                          'can_publish':proof['can_publish'],'reasons':proof['reasons'],'scope':proof['scope']})
        published = any(d.get('status')=='published' for d in drafts)
        verified = any(w.get('domains') and all(d.get('state')=='verified' for d in w['domains'].values()) for w in widgets)
        active = any(w.get('state')=='published' and w.get('active_version') for w in widgets)
        steps = [('verify', bool(tenant.get('email_verified')), '/onboarding'),
                 ('configure', bool(drafts), '/setup'), ('test', any(d['can_publish'] for d in ready) or published, '/testing'),
                 ('publish', published, '/setup'), ('domain', verified, '/widgets'), ('widget_published', active and verified, '/widgets')]
        def elapsed_to(kind):
            if not tenant.get('created_at'):return None
            with self.store.lock:
                record=self.store.db.execute("SELECT created_at FROM operations_events WHERE tenant_id=? AND json_extract(data,'$.kind')=? AND (?!='ux_test' OR json_extract(data,'$.verdict')='PASS') ORDER BY created_at LIMIT 1",(actor.tenant_id,kind,kind)).fetchone()
            if not record:return None
            seconds=(datetime.fromisoformat(record['created_at'])-datetime.fromisoformat(tenant['created_at'])).total_seconds()
            return int(seconds) if seconds>=0 else None
        return {'steps':[{'key':key,'complete':done,'path':path} for key,done,path in steps], 'drafts':ready,
                'complete':all(done for _,done,_ in steps) and not truncated and not widget_truncated,
                'truncated':truncated or widget_truncated, 'status':'TESTED_LOCAL_CONFIGURATION',
                'live_status':'NOT_INDEPENDENTLY_VERIFIED',
                'adoption_metrics':{'time_to_first_pass_seconds':elapsed_to('ux_test'),'time_to_first_published_widget_seconds':elapsed_to('widget_version'),
                    'source':'EXISTING_SERVER_RECORD_TIMESTAMPS','cohort_completion_and_dropoff':'UNAVAILABLE_NO_COHORT_TRACKING'}}

    def health(self, actor):
        actor.require('read')
        drafts, truncated = self.rows(actor.tenant_id,'operations_events',kind='ux_draft',limit=100)
        connections, _ = self.rows(actor.tenant_id,'operations_events',kind='google_connection',limit=20)
        jobs, jobs_truncated = self.rows(actor.tenant_id,'jobs')
        agents = self.store.list('agents',actor.tenant_id)
        items = []
        for assistant in self.store.list('assistants',actor.tenant_id):
            matching = [d for d in drafts if d.get('target_assistant_id')==assistant['id'] or d.get('published_assistant_id')==assistant['id']]
            draft = next((d for d in matching if d.get('status')=='draft'),None)
            proof = self.ux.readiness(actor,draft) if draft else None
            items.append({'id':assistant['id'],'name':assistant['name'],'locales':assistant.get('supported_locales',[]),
                'knowledge_entries':len(assistant.get('faq_entries',[])), 'tool_count':len(assistant.get('allowed_tools',[])),
                'agents_enabled':all(any(a['id']==identity and a.get('enabled') for a in agents) for identity in assistant['assigned_agents']),
                'llm_status':'MOCK' if assistant.get('llm_provider')=='mock' else 'CONFIGURED_UNVERIFIED',
                'draft_id':draft['id'] if draft else None,'readiness':proof,
                'published_draft_id':next((d['id'] for d in matching if d.get('status')=='published'),None),
                'voice_live_verified':False})
        return {'assistants':items,'connections':[{'kind':c.get('connection'),'state':c.get('state'),'certification':'NOT_CERTIFIED'} for c in connections],
                'unresolved_jobs':sum(j.get('status') in ('dead_letter','uncertain','failed') for j in jobs),
                'truncated':truncated or jobs_truncated, 'evidence_scope':'LOCAL_TEXT_TESTS', 'observed_at':self.clock().isoformat()}

    def suggestions(self, actor):
        actor.require('execute')
        tests, truncated = self.rows(actor.tenant_id,'operations_events',kind='ux_test',limit=500)
        jobs, more = self.rows(actor.tenant_id,'jobs')
        signals = [('regression_failure',t,'operations_events') for t in tests if t.get('verdict')!='PASS']
        signals += [('delivery_uncertain' if j.get('status')=='uncertain' else 'provider_failure',j,'jobs') for j in jobs if j.get('status') in ('dead_letter','uncertain','failed')]
        tools, tools_more = self.rows(actor.tenant_id,'tool_executions')
        signals += [('tool_failure',t,'tool_executions') for t in tools if t.get('status') in ('failed','denied') or t.get('outcome',{}).get('status') in ('failed','denied')]
        reported, reported_more = self.rows(actor.tenant_id,'operations_events',kind='quality_signal')
        signals += [(r['category'],r,'operations_events') for r in reported if not r.get('redacted') and r.get('expires_at','')>self.clock().isoformat()]
        if getattr(self.store,'operations',None):
            for trace in self.store.operations.snapshot(actor.tenant_id)['voice_trace']:
                if trace.get('stage')=='confirmation_evaluated' and trace.get('decision')=='unclear':
                    signals.append(('ambiguous_consent',{'id':event_key('voice-trace',str(trace.get('monotonic_ms'))+':'+str(trace.get('correlation_id'))),'scenario':'ambiguous','scope':'PROCESS_METADATA'},'process_voice_trace'))
        reviews, _ = self.rows(actor.tenant_id,'operations_events',kind='quality_review')
        decisions = {r['signal_key']:r['decision'] for r in reversed(reviews) if not r.get('redacted') and r.get('expires_at',self.clock().isoformat())>=self.clock().isoformat()}
        items=[]
        for category,row,table in signals[:100]:
            key=event_key('quality',table+':'+row['id'])
            items.append({'id':key,'category':category,'source_id':row['id'],'source_table':table,
                'scenario':row.get('scenario') if row.get('scenario') in self.ux_scenarios else self.signal_scenarios.get(category,'handoff'),
                'locales':['bg-BG','en-US'],'decision':decisions.get(key,'pending'),'scope':'SUGGESTION_ONLY',
                'provenance':'OPERATOR_REPORTED' if row.get('kind')=='quality_signal' else 'RECORDED_METADATA'})
        return {'suggestions':items,'groups':dict(Counter(category for category,_,_ in signals)),'truncated':truncated or more or tools_more or reported_more or len(signals)>100,
                'live_mutation':False,'analysis_method':'STRUCTURED_RULES_NO_TRANSCRIPT_ANALYSIS'}

    ux_scenarios={'booking','rejection','ambiguous','occupied','language_switch','handoff','interruption','faq','greeting','short_confirmation'}
    signal_scenarios={'stt_uncertainty':'short_confirmation','ambiguous_consent':'ambiguous','tool_denial':'handoff','provider_outage':'handoff','knowledge_gap':'faq','invalid_answer':'faq','duplicate_action':'booking','abandonment':'greeting'}

    def report_signal(self,actor,conversation,payload):
        actor.require('approve');self.store.get('conversations',actor.tenant_id,conversation)
        key=event_key('quality-report',conversation+':'+payload.event_id)
        with self.store.transaction():
            previous=self.store.find('operations_events',actor.tenant_id,key)
            if previous:
                if previous.get('category')!=payload.category:raise DomainError('conflict',409)
                return {'id':previous['id'],'duplicate':True}
            active,_=self.rows(actor.tenant_id,'operations_events',kind='quality_signal')
            if sum(not r.get('redacted') and r.get('expires_at','')>self.clock().isoformat() for r in active)>=500:raise DomainError('limit_reached',429)
            expiry=(self.clock()+timedelta(days=min(7,self.store.tenant(actor.tenant_id)['retention_days']))).isoformat()
            row=self.store.add('operations_events',actor.tenant_id,{'kind':'quality_signal','conversation_id':conversation,'category':payload.category,
                'timestamp':self.clock().isoformat(),'expires_at':expiry,'actor_id':actor.user_id},external_key=key)
            self.store.audit(actor,'quality:reported',resource_id=row['id'])
            return {'id':row['id'],'duplicate':False}

    def review(self, actor, identity, payload):
        actor.require('approve')
        with self.store.transaction():
            if identity not in {s['id'] for s in self.suggestions(actor)['suggestions']}:raise DomainError('not_found',404)
            key='quality-review:'+actor.user_id+':'+identity
            previous=self.store.find('operations_events',actor.tenant_id,key)
            data={'kind':'quality_review','signal_key':identity,'decision':payload.decision,'reviewer_id':actor.user_id,'timestamp':now(),
                  'expires_at':(self.clock()+timedelta(days=min(7,self.store.tenant(actor.tenant_id)['retention_days']))).isoformat()}
            self.store.update('operations_events',actor.tenant_id,previous['id'],data) if previous else self.store.add('operations_events',actor.tenant_id,data,external_key=key)
            self.store.audit(actor,'quality:reviewed',resource_id=identity)
        return {'decision':payload.decision,'live_mutation':False}

    def purge(self):
        with self.store.transaction():
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE json_extract(data,'$.kind') IN ('quality_signal','quality_review') AND coalesce(json_extract(data,'$.redacted'),0)=0 AND json_extract(data,'$.expires_at')<=? LIMIT 500",(self.clock().isoformat(),)).fetchall()
            for record in rows:
                row=json.loads(record['data']);self.store.update('operations_events',row['tenant_id'],row['id'],{'category':None,'decision':None,'redacted':True})
        return len(rows)

    def operations_targets(self,actor,payload=None):
        actor.require('configure' if payload else 'read')
        key='operations-targets'
        with self.store.transaction():
            row=self.store.find('operations_events',actor.tenant_id,key)
            if payload:
                data={'kind':'operations_targets','targets':payload.model_dump(),'timestamp':self.clock().isoformat()}
                row=self.store.update('operations_events',actor.tenant_id,row['id'],data) if row else self.store.add('operations_events',actor.tenant_id,data,external_key=key)
                self.store.audit(actor,'operations:targets_saved',resource_id=row['id'])
        jobs,truncated=self.rows(actor.tenant_id,'jobs')
        return {'targets':row['targets'] if row else None,'evaluation':'NOT_EVALUATED_REQUIRED_WINDOW_NOT_OBSERVED','error_budget_remaining':None,
                'backlog':dict(Counter(job.get('status','unknown') for job in jobs)),'truncated':truncated,'scope':'INTERNAL_TARGETS_NOT_A_CUSTOMER_SLA'}

    def usage(self, actor, period):
        actor.require('read')
        current=self.billing.entitlements.period()
        with self.store.lock:
            rows=self.store.db.execute("SELECT strftime('%Y-%m-%d',json_extract(data,'$.timestamp')) AS day,json_extract(data,'$.category') AS category,json_extract(data,'$.provider') AS provider,json_extract(data,'$.unit') AS unit,json_extract(data,'$.assistant_id') AS assistant_id,json_extract(data,'$.channel') AS channel,sum(json_extract(data,'$.quantity')) AS quantity FROM billing_usage WHERE tenant_id=? AND json_extract(data,'$.billing_period')=? GROUP BY day,category,provider,unit,assistant_id,channel ORDER BY day,category,provider LIMIT 1001",(actor.tenant_id,period)).fetchall()
        groups=[dict(r) for r in rows[:1000]]
        for group in groups:group['quantity_text']=str(group['quantity'])
        summary=self.billing.entitlements.summary(actor.tenant_id) if period==current else None
        forecast=[]
        at=self.clock().astimezone(timezone.utc)
        elapsed=int((at-at.replace(day=1,hour=0,minute=0,second=0,microsecond=0)).total_seconds())
        if period==current and elapsed>=86400 and len(rows)<=1000:
            totals={}
            for group in groups:totals[(group['category'],group['unit'])]=totals.get((group['category'],group['unit']),0)+group['quantity']
            seconds=calendar.monthrange(at.year,at.month)[1]*86400
            forecast=[{'category':category,'unit':unit,'estimated_month_quantity_text':str((quantity*seconds+elapsed-1)//elapsed)} for (category,unit),quantity in totals.items()]
        return {'period':period,'timezone':'UTC','groups':groups,'truncated':len(rows)>1000,'current':summary,
            'costs':{'compute_estimate':'UNAVAILABLE','provider_charges':'NOT_RECONCILED','customer_invoices':'SEE_BILLING'},
            'unmeasured_dimensions':['historical_unallocated_assistant_channel','sip_vs_pstn_provider_certification'],
            'forecast':forecast,'forecast_scope':'ESTIMATE_CONSTANT_OBSERVED_AVERAGE_REPORTED_EVENTS_ONLY_NOT_CURRENCY'}

    def requests(self, actor, limit, offset):
        actor.require('read')
        with self.store.lock:
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE tenant_id=? AND json_extract(data,'$.kind')='concierge_request' AND (json_extract(data,'$.expires_at') IS NULL OR json_extract(data,'$.expires_at')>?) ORDER BY created_at DESC,id DESC LIMIT ? OFFSET ?",(actor.tenant_id,now(),limit+1,offset)).fetchall()
        return {'items':[{k:json.loads(r['data']).get(k) for k in ('id','action','status','locale','conversation_id','operator_state','assigned_user_id','request_revision')} for r in rows[:limit]],'has_more':len(rows)>limit}

    def request_detail(self,actor,identity):
        actor.require('approve')
        row=self.store.get('operations_events',actor.tenant_id,identity)
        if row.get('kind')!='concierge_request' or row.get('redacted') or row.get('expires_at','')<=now():raise DomainError('not_found',404)
        self.store.audit(actor,'requests:details_read',resource_id=identity)
        return {k:row.get(k) for k in ('id','name','email','company','topic','timeline','impact')}

    def request_change(self,actor,identity,payload):
        actor.require('approve')
        with self.store.transaction():
            row=self.store.get('operations_events',actor.tenant_id,identity)
            if row.get('kind')!='concierge_request' or row.get('redacted') or row.get('expires_at','')<=now():raise DomainError('not_found',404)
            if row.get('request_revision',0)!=payload.revision:raise DomainError('conflict',409)
            if payload.assigned_user_id:
                user=self.store.get('users',actor.tenant_id,payload.assigned_user_id)
                if not user.get('enabled') or user['role'] not in ('admin','operator'):raise DomainError('forbidden',403)
            self.store.update('operations_events',actor.tenant_id,identity,{'operator_state':payload.state,'assigned_user_id':payload.assigned_user_id,'request_revision':payload.revision+1})
            self.store.audit(actor,'requests:state_changed',resource_id=identity)
        return {'revision':payload.revision+1,'state':payload.state,'provider_message_sent':False}

    def analytics(self, actor, days):
        actor.require('read')
        since=(self.clock()-timedelta(days=days)).isoformat()
        with self.store.lock:
            conversations=self.store.db.execute("SELECT json_extract(data,'$.channel') channel,json_extract(data,'$.active_locale') locale,count(*) quantity FROM conversations WHERE tenant_id=? AND created_at>=? GROUP BY channel,locale",(actor.tenant_id,since)).fetchall()
            appointments=self.store.db.execute("SELECT json_extract(data,'$.status') status,count(*) quantity FROM appointments WHERE tenant_id=? AND created_at>=? GROUP BY status",(actor.tenant_id,since)).fetchall()
            funnel=self.store.db.execute("SELECT json_extract(data,'$.stage') stage,json_extract(data,'$.scope') scope,json_extract(data,'$.locale') locale,json_extract(data,'$.assistant_ref') assistant_ref,count(*) quantity FROM operations_events WHERE tenant_id=? AND created_at>=? AND json_extract(data,'$.kind')='journey_event' AND coalesce(json_extract(data,'$.redacted'),0)=0 AND json_extract(data,'$.expires_at')>? GROUP BY stage,scope,locale,assistant_ref",(actor.tenant_id,since,self.clock().isoformat())).fetchall()
        return {'days':days,'scope':'OPERATIONAL_RECORD_COUNTS_NOT_CONVERSION','conversations':[dict(r) for r in conversations],
                'appointments':[dict(r) for r in appointments],'behavioral_tracking':'OPTIONAL_EXPLICIT_CONSENT_ONLY','funnel':[dict(r) for r in funnel],
                'funnel_unmeasured':['all_impressions','all_opened_sessions','sales_qualification','reminder_received','attended'],'revenue':'UNAVAILABLE',
                'raw_content_included':False,'retention_days':self.store.tenant(actor.tenant_id)['retention_days']}


def register_customer_workspace(app, store, actor, billing, clock):
    service=CustomerWorkspace(store,app.state.ux,billing,clock)
    app.state.customer_workspace=service
    @app.get('/api/workspace/progress')
    def progress(principal=Depends(actor)):return service.progress(principal)
    @app.get('/api/workspace/health')
    def health(principal=Depends(actor)):return service.health(principal)
    @app.get('/api/workspace/quality')
    def quality(principal=Depends(actor)):return service.suggestions(principal)
    @app.post('/api/workspace/quality/{identity}/review')
    def review(identity:str,payload:Review,principal=Depends(actor)):return service.review(principal,identity,payload)
    @app.post('/api/workspace/quality-signals/{conversation}')
    def report(conversation:str,payload:QualitySignal,principal=Depends(actor)):return service.report_signal(principal,conversation,payload)
    @app.get('/api/workspace/usage')
    def usage(period:str=Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),principal=Depends(actor)):return service.usage(principal,period)
    @app.get('/api/workspace/requests')
    def requests(limit:int=Query(default=25,ge=1,le=100),offset:int=Query(default=0,ge=0,le=100000),principal=Depends(actor)):return service.requests(principal,limit,offset)
    @app.get('/api/workspace/requests/{identity}')
    def request_detail(identity:str,principal=Depends(actor)):return service.request_detail(principal,identity)
    @app.put('/api/workspace/requests/{identity}')
    def request_change(identity:str,payload:RequestChange,principal=Depends(actor)):return service.request_change(principal,identity,payload)
    @app.get('/api/workspace/analytics')
    def analytics(days:int=Query(default=30,ge=1,le=90),principal=Depends(actor)):return service.analytics(principal,days)
    @app.get('/api/workspace/operations-targets')
    def targets(principal=Depends(actor)):return service.operations_targets(principal)
    @app.put('/api/workspace/operations-targets')
    def save_targets(payload:OperationsTargets,principal=Depends(actor)):return service.operations_targets(principal,payload)
