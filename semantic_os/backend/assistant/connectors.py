"""Explicitly enabled local connector fixtures. Never exchanges real OAuth credentials."""
from typing import Literal
from pydantic import Field, field_validator,model_validator
from .domain import Contract, DomainError
from .connector_adapters import OfflineProviderHTTP,ProviderAdapter,calendly_signature
from .connector_oauth import ConnectorOAuth
from datetime import datetime,timezone
from hashlib import sha256
import json

CAPABILITIES = {
    'google': ['availability', 'create', 'reschedule', 'cancel'],
    'outlook': ['availability', 'create', 'reschedule', 'cancel'],
    'calendly': ['availability', 'scheduled_events'],
    'hubspot': ['contact_read', 'contact_write'],
}

class ConnectionInput(Contract):
    provider: Literal['google', 'outlook', 'calendly', 'hubspot']
    actions: list[str] = Field(min_length=1, max_length=8)
    resource_ids: list[str] = Field(min_length=1, max_length=8)

    @field_validator('resource_ids')
    @classmethod
    def fixture_resources(cls, values):
        import re
        if any(not re.fullmatch(r'fixture-[a-z0-9_-]{1,60}', value) for value in values):
            raise ValueError('Synthetic resources required')
        if len(set(values)) != len(values):raise ValueError('Duplicate resource')
        return values

class ConnectionAction(Contract):
    revision: int = Field(ge=1)
    scenario: Literal['connect', 'expired', 'failure', 'unknown'] = 'connect'
    locale: Literal['bg-BG', 'en-US'] = 'en-US'

class OAuthComplete(Contract):
    state:str=Field(min_length=10,max_length=200)
    binding:str=Field(min_length=10,max_length=200)
    code:Literal['fixture-code']='fixture-code'

class ProviderPreview(Contract):
    revision:int=Field(ge=1)
    action:str=Field(min_length=1,max_length=40)
    resource_id:str=Field(min_length=1,max_length=150)
    key:str=Field(min_length=1,max_length=100)
    consent:bool=False
    account_type:Literal['work','personal','shared']='work'
    arguments:dict=Field(default_factory=dict,max_length=8)
    locale:Literal['bg-BG','en-US']='en-US'

class QuoteInput(Contract):
    tier:Literal['simple','advanced','enterprise']
    system:Literal['crm','erp','legacy','rest']
    objects:list[Literal['contacts','appointments','leads','inventory','orders']]=Field(min_length=1,max_length=5)
    direction:Literal['one_way','bidirectional']
    authentication:Literal['oauth','service_account','api_key','unknown']
    environments:int=Field(ge=1,le=10)
    custom_sla:bool=False
    key:str=Field(min_length=1,max_length=100)
    @model_validator(mode='after')
    def scope_tier(self):
        if len(set(self.objects))!=len(self.objects):raise ValueError('Duplicate object')
        if self.tier=='simple' and (self.direction!='one_way' or self.environments!=1 or self.custom_sla or len(self.objects)>2):raise ValueError('Simple scope requires advanced review')
        return self

PRICES={'simple':{'setup_min_eur':500,'setup_max_eur':1500,'maintenance_eur':99},
        'advanced':{'setup_min_eur':1500,'setup_max_eur':5000,'maintenance_eur':199},
        'enterprise':{'setup_min_eur':5000,'setup_max_eur':None,'maintenance_eur':None}}

class ConnectorService:
    def __init__(self, store, secrets, *, enabled=False,transport=None,clock=None):
        self.store, self.secrets, self.enabled = store, secrets, enabled
        from .connector_fixtures import fixture_transport
        self.clock=clock or (lambda:datetime.now(timezone.utc))
        self.http=OfflineProviderHTTP(transport or fixture_transport())
        self.oauth=ConnectorOAuth(self,self.http,self.clock)

    def guard(self, principal, *, recovery=False):
        principal.require('configure')
        if not self.enabled:raise DomainError('unconfigured',503)
        if self.store.entitlements:self.store.entitlements.access(principal.tenant_id,recovery=recovery)

    def catalog(self, principal):
        self.guard(principal)
        return [{'provider': provider, 'contract_version': 1, 'availability': 'COMING_SOON',
                 'fixture_actions': actions, 'simulation': True} for provider, actions in CAPABILITIES.items()]

    @staticmethod
    def project(row):
        return {key: row.get(key) for key in ('id','contract_version','provider','state','actions','resource_ids','revision','simulation','failure_code')}

    def row(self, principal, identity):
        row=self.store.get('operations_events',principal.tenant_id,identity)
        if row.get('kind')!='connector_fixture':raise DomainError('not_found',404)
        return row

    def list(self, principal):
        self.guard(principal,recovery=True)
        return [self.project(row) for row in self.store.list('operations_events',principal.tenant_id) if row.get('kind')=='connector_fixture']

    def create(self, principal, payload):
        self.guard(principal)
        if len(set(payload.actions))!=len(payload.actions) or set(payload.actions)-set(CAPABILITIES[payload.provider]):raise DomainError('invalid_input',422)
        import json
        from hashlib import sha256
        key='connector-fixture:'+sha256(json.dumps({'provider':payload.provider,'actions':sorted(payload.actions),'resources':sorted(payload.resource_ids)},sort_keys=True).encode()).hexdigest()
        with self.store.transaction():
            existing=self.store.find('operations_events',principal.tenant_id,key)
            if existing:return self.project(existing)
            if self.store.entitlements:self.store.entitlements.check_connector(principal.tenant_id,payload.provider,creating=True)
            row=self.store.add('operations_events',principal.tenant_id,{
                'kind':'connector_fixture','contract_version':1,**payload.model_dump(),
                'state':'disconnected','revision':1,'simulation':True,'failure_code':None},external_key=key)
            self.store.audit(principal,'connector:fixture_created',resource_id=row['id'])
        return self.project(row)

    def test(self, principal, identity, payload):
        self.guard(principal)
        with self.store.transaction():
            row=self.row(principal,identity)
            if row['revision']!=payload.revision:raise DomainError('conflict',409)
            if self.store.entitlements:self.store.entitlements.check_connector(principal.tenant_id,row['provider'])
            state={'connect':'connected','expired':'needs_reauthorization','failure':'degraded','unknown':'degraded'}[payload.scenario]
            failure={'connect':None,'expired':'oauth_expired','failure':'provider_error','unknown':'delivery_unknown'}[payload.scenario]
            # Unknown simulated writes cannot be cleared by another test or reconnect.
            if row.get('failure_code')=='delivery_unknown':raise DomainError('delivery_unknown',409)
            self.secrets.put(principal.tenant_id,'connector:fixture:'+identity,
                             'fixture-token' if state=='connected' else '{}',principal)
            row=self.store.update('operations_events',principal.tenant_id,identity,{
                'state':state,'revision':row['revision']+1,'failure_code':failure,'oauth_verified':False})
            self.store.audit(principal,'connector:fixture_tested',resource_id=identity)
            return {**self.project(row),'locale':payload.locale,'result':'SIMULATED',
                    'retry_allowed':failure!='delivery_unknown'}

    def disconnect(self, principal, identity, payload):
        self.guard(principal,recovery=True)
        with self.store.transaction():
            row=self.row(principal,identity)
            if row['revision']!=payload.revision:raise DomainError('conflict',409)
            self.secrets.put(principal.tenant_id,'connector:fixture:'+identity,'{}',principal)
            self.secrets.put(principal.tenant_id,'connector:oauth:'+identity,'{}',principal)
            row=self.store.update('operations_events',principal.tenant_id,identity,{
                'state':'disconnected','revision':row['revision']+1,'oauth_verified':False})
            self.store.audit(principal,'connector:fixture_disconnected',resource_id=identity)
        return self.project(row)

    def resources(self,principal,identity):
        self.guard(principal);row=self.row(principal,identity)
        if self.store.entitlements:self.store.entitlements.check_connector(principal.tenant_id,row['provider'])
        return {'simulation':True,'resources':ProviderAdapter(row['provider'],self.http).resources(self.oauth.token(principal,row))}

    def preview(self,principal,identity,payload):
        self.guard(principal)
        with self.store.transaction():
            row=self.row(principal,identity)
            if row['revision']!=payload.revision:raise DomainError('conflict',409)
            if payload.action not in row['actions'] or payload.resource_id not in row['resource_ids']:raise DomainError('forbidden',403)
            if row.get('failure_code')=='delivery_unknown':raise DomainError('delivery_unknown',409)
            if self.store.entitlements:self.store.entitlements.check_connector(principal.tenant_id,row['provider'])
            key='connector-preview:'+sha256((identity+':'+payload.key).encode()).hexdigest()
            fingerprint=sha256(json.dumps(payload.model_dump(),sort_keys=True).encode()).hexdigest()
            receipt=self.store.find('operations_events',principal.tenant_id,key)
            if receipt:
                if receipt['fingerprint']!=fingerprint:raise DomainError('conflict',409)
                if receipt['status']!='done':raise DomainError('delivery_unknown',409)
                return receipt['result']
            token=self.oauth.token(principal,row)
            # Never route an unconfirmed write through even a fixture adapter.
            if payload.action in ('create','reschedule','cancel','contact_write') and not payload.consent:raise DomainError('forbidden',403)
            receipt=self.store.add('operations_events',principal.tenant_id,{'kind':'connector_preview','connection_id':identity,'status':'pending','fingerprint':fingerprint},external_key=key)
        try:
            result=ProviderAdapter(row['provider'],self.http).execute(token,payload.action,payload.resource_id,payload.arguments,key,
                account_type=payload.account_type,owned=True,consent=payload.consent)
            result={**result,'simulation':True,'locale':payload.locale}
        except DomainError as error:
            with self.store.transaction():
                self.store.update('operations_events',principal.tenant_id,receipt['id'],{'status':'unknown' if error.code=='delivery_unknown' else 'failed','failure_code':error.code})
                current=self.row(principal,identity)
                if current['revision']==row['revision']:
                    self.store.update('operations_events',principal.tenant_id,identity,{'state':'degraded','revision':current['revision']+1,'failure_code':error.code})
            raise
        with self.store.transaction():
            self.store.update('operations_events',principal.tenant_id,receipt['id'],{'status':'done','result':result})
        return result

    def webhook(self,principal,identity,raw,header):
        self.guard(principal);row=self.row(principal,identity)
        if row['provider']!='calendly' or row['state']!='connected':raise DomainError('forbidden',403)
        digest=calendly_signature(raw,header,'fixture-webhook-secret',self.clock())
        body=json.loads(raw)
        if body.get('event') not in ('invitee.created','invitee.canceled') or body.get('payload',{}).get('event')!='fixture-primary':raise DomainError('invalid_input',422)
        key='connector-webhook:'+sha256((identity+digest).encode()).hexdigest()
        with self.store.transaction():
            if self.store.find('operations_events',principal.tenant_id,key):return {'simulation':True,'duplicate':True}
            self.store.add('operations_events',principal.tenant_id,{'kind':'connector_webhook_receipt','event':body['event'],'connection_id':identity},external_key=key)
        return {'simulation':True,'duplicate':False}

    def quotes(self,principal):
        self.guard(principal,recovery=True)
        return [row for row in self.store.list('operations_events',principal.tenant_id) if row.get('kind')=='connector_quote']
    def quote(self,principal,payload):
        self.guard(principal)
        key='connector-quote:'+sha256(payload.key.encode()).hexdigest();data=payload.model_dump(exclude={'key'})
        fingerprint=sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()
        with self.store.transaction():
            old=self.store.find('operations_events',principal.tenant_id,key)
            if old:
                if old['fingerprint']!=fingerprint:raise DomainError('conflict',409)
                return old
            row=self.store.add('operations_events',principal.tenant_id,{'kind':'connector_quote','requirements':data,'fingerprint':fingerprint,
                'pricing':PRICES[payload.tier],'status':'SCOPING_REQUIRED','commercial_approval':False,'subscription_separate':True,'simulation':True,
                'review_required':['field_mapping','security','effort','sla','acceptance_tests','rollback','commercial_owner']},external_key=key)
            self.store.audit(principal,'connector:quote_requested',resource_id=row['id'])
        return row

def register_connectors(app, service, actor):
    from fastapi import Depends
    from .domain import Principal
    @app.get('/api/connectors')
    def catalog(principal:Principal=Depends(actor)):return service.catalog(principal)
    @app.get('/api/connectors/connections')
    def connections(principal:Principal=Depends(actor)):return service.list(principal)
    @app.post('/api/connectors/connections')
    def create(payload:ConnectionInput,principal:Principal=Depends(actor)):return service.create(principal,payload)
    @app.post('/api/connectors/connections/{identity}/test')
    def test(identity:str,payload:ConnectionAction,principal:Principal=Depends(actor)):return service.test(principal,identity,payload)
    @app.post('/api/connectors/connections/{identity}/disconnect')
    def disconnect(identity:str,payload:ConnectionAction,principal:Principal=Depends(actor)):return service.disconnect(principal,identity,payload)
    @app.post('/api/connectors/connections/{identity}/oauth/start')
    def oauth_start(identity:str,payload:ConnectionAction,principal:Principal=Depends(actor)):return service.oauth.start(principal,identity,payload.revision)
    @app.post('/api/connectors/connections/{identity}/oauth/complete')
    def oauth_complete(identity:str,payload:OAuthComplete,principal:Principal=Depends(actor)):return service.oauth.complete(principal,identity,payload.state,payload.binding,payload.code)
    @app.get('/api/connectors/connections/{identity}/resources')
    def resources(identity:str,principal:Principal=Depends(actor)):return service.resources(principal,identity)
    @app.post('/api/connectors/connections/{identity}/preview')
    def preview(identity:str,payload:ProviderPreview,principal:Principal=Depends(actor)):return service.preview(principal,identity,payload)
    @app.get('/api/connectors/quotes')
    def quotes(principal:Principal=Depends(actor)):return service.quotes(principal)
    @app.post('/api/connectors/quotes')
    def quote(payload:QuoteInput,principal:Principal=Depends(actor)):return service.quote(principal,payload)
