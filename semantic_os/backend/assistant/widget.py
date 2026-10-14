"""Public widget admission is a restricted capability, never staff authentication."""
from datetime import datetime, timedelta
from hashlib import sha256
import hmac
import html
import http.client
import ipaddress
import json
import os
import re
from pathlib import Path
import secrets
import socket
import ssl
from typing import Literal
from urllib.parse import urlsplit
from fastapi import Depends, Request
from fastapi.responses import HTMLResponse, Response, JSONResponse
from pydantic import Field, field_validator, StrictBool
from .domain import Contract, DomainError, Incoming, Locale, Principal
from .store import uid
from .ux import digest

PUBLIC_TOOLS = {'CheckAvailability', 'CreateAppointment', 'EscalateToHuman'}
CONCIERGE_TOOLS={'ConciergeAvailability','ConciergeBooking','ConciergeManage','ConciergeRequest','EscalateToHuman'}


def origin(value, local=False):
    parsed=urlsplit(value)
    if (parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ('','/')
        or not parsed.hostname or parsed.scheme not in ('http','https')): raise ValueError('invalid origin')
    if parsed.scheme!='https' and not (local and parsed.hostname in ('127.0.0.1','localhost')): raise ValueError('https required')
    hostname=parsed.hostname.encode('idna').decode().lower()
    if len(hostname)>253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?',label) for label in hostname.split('.')):raise ValueError('invalid hostname')
    try:
        address=ipaddress.ip_address(hostname)
        if not (local and address.is_loopback): raise ValueError('literal address forbidden')
    except ValueError as error:
        if 'forbidden' in str(error): raise
    if any(c in hostname for c in ('*','[',']',"'",'"','<','>')): raise ValueError('invalid origin')
    port=parsed.port
    suffix='' if not port or port=={'http':80,'https':443}[parsed.scheme] else ':'+str(port)
    return parsed.scheme+'://'+hostname+suffix


class WidgetSettings(Contract):
    analytics_enabled:StrictBool=False
    assistant_id: str
    origins: list[str] = Field(min_length=1,max_length=5)
    color: str = Field(default='#1d4ed8',pattern=r'^#[0-9a-fA-F]{6}$')
    appearance: Literal['default','ontelyx-dark'] = 'default'
    logo_url: str = Field(default='',max_length=500)
    greetings: dict[Locale,str]
    privacy_notices: dict[Locale,str]
    faq_approved: bool = False
    booking_enabled: bool = True
    concierge_enabled: bool = False
    retention_days: int = Field(default=7,ge=1,le=30)
    daily_sessions: int = Field(default=100,ge=1,le=500)
    daily_messages: int = Field(default=1000,ge=10,le=3000)

    @field_validator('greetings','privacy_notices')
    @classmethod
    def bilingual(cls,value):
        if set(value)!={'bg-BG','en-US'} or any(not text.strip() or len(text)>1000 for text in value.values()): raise ValueError('both languages required')
        return value

    @field_validator('logo_url')
    @classmethod
    def logo(cls,value):
        if value:
            parsed=urlsplit(value)
            if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment: raise ValueError('unsafe logo')
        return value


class WidgetPublish(Contract):
    draft_id: str
    confirmed: bool = False


class WidgetAction(Contract):
    confirmed: bool = False
    version_id: str | None = None


class DomainProof(Contract):
    origin: str


class Admission(Contract):
    locale: Literal['auto','bg-BG','en-US'] = 'auto'


class Redeem(Contract):
    ticket: str = Field(min_length=32,max_length=100)
    parent_origin: str = Field(max_length=250)
    locale: Locale


class WidgetMessage(Contract):
    content: str = Field(min_length=1,max_length=2000)
    event_id: str = Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    locale: Locale | None = None


def domain_file(site, public_id, allowed_local, demo_targets=None):
    """GET only a fixed nonce path, pinned address, no proxy/redirect/private DNS."""
    parsed=urlsplit(site)
    local=site in allowed_local
    target=(demo_targets or {}).get(site) if local else None
    host,port=(target[0],int(target[1])) if target else (parsed.hostname,parsed.port or (443 if parsed.scheme=='https' else 80))
    addresses=list({item[4][0] for item in socket.getaddrinfo(host,port,type=socket.SOCK_STREAM)})
    if not addresses or any(not ipaddress.ip_address(item).is_global and not (local and (target or ipaddress.ip_address(item).is_loopback)) for item in addresses): raise DomainError('forbidden',403)
    address=addresses[0]
    connection=http.client.HTTPConnection(address,port,timeout=3)
    if parsed.scheme=='https':
        connection.connect()
        connection.sock=ssl.create_default_context().wrap_socket(connection.sock,server_hostname=parsed.hostname)
    try:
        connection.request('GET','/.well-known/testmid-widget/'+public_id+'.txt',headers={'Host':parsed.netloc,'Accept':'text/plain','User-Agent':'TestMidDomainVerification/1'})
        response=connection.getresponse()
        if response.status!=200 or 'text/plain' not in response.getheader('Content-Type',''): raise DomainError('verification_required',409)
        data=response.read(513)
        if len(data)>512: raise DomainError('invalid_input',422)
        return data.decode('ascii').strip()
    finally: connection.close()


class WidgetService:
    def __init__(self,store,orchestrator,ux,*,public_origin='',local_sites=(),clock=None,fetch_domain=domain_file):
        self.store,self.engine,self.ux=store,orchestrator,ux
        self.clock=clock or orchestrator.clock
        self.public_origin=origin(public_origin,local=bool(local_sites)) if public_origin else ''
        self.local_sites=set(local_sites)
        self.fetch_domain=fetch_domain
        from .journey import Journey
        self.journey=Journey(store,self.clock)

    def rows(self,tenant,kind): return [row for row in self.store.list('operations_events',tenant) if row.get('kind')==kind]

    def get(self,principal,identity):
        principal.require('configure')
        row=self.store.get('operations_events',principal.tenant_id,identity)
        if row.get('kind')!='widget_integration':raise DomainError('not_found',404)
        return row

    def signature(self,tenant):
        business=self.store.tenant(tenant)
        return digest({'business':{key:business.get(key) for key in ('timezone','calendar_policy')},
            'agents':[{key:row.get(key) for key in ('id','enabled','allowed_tools','instructions','supported_locales')} for row in self.store.list('agents',tenant)]})

    def resolve(self,public_id,published=True,privacy=False):
        if not self.public_origin:raise DomainError('unconfigured',503)
        with self.store.lock:
            found=self.store.db.execute("SELECT data FROM operations_events WHERE external_key=? AND json_extract(data,'$.kind')='widget_integration'",('widget:'+public_id,)).fetchall()
        if len(found)!=1:raise DomainError('not_found',404)
        row=json.loads(found[0]['data'])
        if row['state']=='revoked' and not privacy or published and (row['state']!='published' or not row.get('active_version')):raise DomainError('disabled',403)
        return row

    def configure(self,principal,payload,identity=None):
        principal.require('configure')
        if not self.public_origin:raise DomainError('unconfigured',503)
        self.store.get('assistants',principal.tenant_id,payload.assistant_id)
        if payload.retention_days>self.store.tenant(principal.tenant_id)['retention_days']:raise DomainError('invalid_input',422)
        try: sites=[origin(value,local=True) for value in payload.origins]
        except (ValueError,UnicodeError):raise DomainError('invalid_input',422) from None
        if self.public_origin in sites or len(set(sites))!=len(sites) or any(urlsplit(site).scheme=='http' and site not in self.local_sites for site in sites):raise DomainError('forbidden',403)
        with self.store.transaction():
            old=self.get(principal,identity) if identity else None
            if old and old['assistant_id']!=payload.assistant_id:raise DomainError('conflict',409)
            if old and old['state']=='revoked':raise DomainError('disabled',409)
            if not old and len(self.rows(principal.tenant_id,'widget_integration'))>=10:raise DomainError('limit_reached',429)
            settings=payload.model_dump();settings['origins']=sites
            data={'kind':'widget_integration','assistant_id':payload.assistant_id,'settings':settings,
                'public_id':old['public_id'] if old else 'wdg_'+uid().replace('-',''), 'state':'draft',
                'epoch':old['epoch']+1 if old else 1,'active_version':None,'domains':{},'updated_at':self.clock().isoformat()}
            for site in sites:
                data['domains'][site]=(old or {}).get('domains',{}).get(site,{'state':'pending'})
            if old:data.pop('assistant_id')  # Binding was checked above; Store forbids even same-value rewrites.
            result=self.store.update('operations_events',principal.tenant_id,identity,data) if old else self.store.add('operations_events',principal.tenant_id,data,external_key='widget:'+data['public_id'])
            self.store.audit(principal,'widget:configured',resource_id=result['id'])
            return result

    def challenge(self,principal,identity,site):
        row=self.get(principal,identity)
        if row['state']=='revoked':raise DomainError('disabled',409)
        if site not in row['settings']['origins']:raise DomainError('forbidden',403)
        nonce=secrets.token_urlsafe(32)
        domains={**row['domains'],site:{'state':'pending','hash':sha256(nonce.encode()).hexdigest(),'expires_at':(self.clock()+timedelta(hours=1)).isoformat()}}
        self.store.update('operations_events',principal.tenant_id,identity,{'domains':domains,'epoch':row['epoch']+1,'state':'draft','active_version':None})
        return {'path':'/.well-known/testmid-widget/'+row['public_id']+'.txt','content':nonce,'expires_at':domains[site]['expires_at'],'origin':site}

    def verify(self,principal,identity,site):
        row=self.get(principal,identity)
        if row['state']=='revoked':raise DomainError('disabled',409)
        proof=row['domains'].get(site,{})
        if not proof.get('hash') or datetime.fromisoformat(proof['expires_at'])<=self.clock():raise DomainError('expired',409)
        try:content=self.fetch_domain(site,row['public_id'],self.local_sites)
        except DomainError:raise
        except (OSError,ValueError,UnicodeError,http.client.HTTPException):raise DomainError('verification_required',409) from None
        if not hmac.compare_digest(proof['hash'],sha256(content.encode()).hexdigest()):raise DomainError('verification_required',409)
        with self.store.transaction():
            fresh=self.get(principal,identity)
            if fresh['state']=='revoked':raise DomainError('disabled',409)
            if fresh['domains'].get(site,{}).get('hash')!=proof['hash']:raise DomainError('conflict',409)
            domains={**fresh['domains'],site:{'state':'verified','verified_at':self.clock().isoformat(),'method':'nonce_file'}}
            result=self.store.update('operations_events',principal.tenant_id,identity,{'domains':domains})
            self.store.audit(principal,'widget:domain_verified',resource_id=identity)
            return result

    def publish(self,principal,identity,payload):
        row=self.get(principal,identity)
        if row['state']=='revoked':raise DomainError('disabled',409)
        if not payload.confirmed:raise DomainError('forbidden',403)
        draft=self.ux.draft(principal,payload.draft_id)
        if draft['status']!='published' or draft.get('published_assistant_id')!=row['assistant_id']:raise DomainError('conflict',409)
        if any(test['verdict']!='PASS' for test in self.ux.readiness(principal,draft)['required_tests']):raise DomainError('conflict',409)
        config=draft['config']
        if draft.get('published_business_hash')!=digest({key:self.store.tenant(principal.tenant_id).get(key) for key in ('timezone','calendar_policy')}):raise DomainError('conflict',409)
        if not self.store.tenant(principal.tenant_id).get('email_verified',True):raise DomainError('verification_required',409)
        current_agents=[{key:record[key] for key in ('id','enabled','instructions','allowed_tools','supported_locales')} for record in self.store.list('agents',principal.tenant_id)]
        expected_signature=self.signature(principal.tenant_id)
        if current_agents!=draft['agents'] or any(not record['enabled'] for record in current_agents):raise DomainError('conflict',409)
        if not config['instructions'].strip() or config['llm_provider']!='mock' or config['status']!='active':raise DomainError('unconfigured',409)
        if config['faq_entries'] and not row['settings']['faq_approved']:raise DomainError('verification_required',409)
        if not all(row['domains'].get(site,{}).get('state')=='verified' for site in row['settings']['origins']):raise DomainError('verification_required',409)
        tools=set(config['allowed_tools']) & (CONCIERGE_TOOLS if row['settings'].get('concierge_enabled') else PUBLIC_TOOLS)
        if row['settings'].get('concierge_enabled') and row['settings']['booking_enabled']:raise DomainError('invalid_input',422)
        if row['settings']['booking_enabled'] and not {'CheckAvailability','CreateAppointment'}<=tools:raise DomainError('tool_denied',403)
        if not row['settings']['booking_enabled']:tools-={'CheckAvailability','CreateAppointment'}
        config={**config,'allowed_tools':sorted(tools),'enabled_channels':['web_chat'],'escalation_rules':{'keywords':[],'pause_automation':True}}
        with self.store.transaction():
            fresh=self.get(principal,identity)
            if fresh['epoch']!=row['epoch']:raise DomainError('conflict',409)
            if self.signature(principal.tenant_id)!=expected_signature:raise DomainError('conflict',409)
            version=self.store.add('operations_events',principal.tenant_id,{'kind':'widget_version','integration_id':identity,'assistant_id':row['assistant_id'],
                'config':config,'settings':row['settings'],'signature':self.signature(principal.tenant_id),'draft_id':draft['id'],'created_at':self.clock().isoformat()})
            result=self.store.update('operations_events',principal.tenant_id,identity,{'state':'published','active_version':version['id'],'epoch':row['epoch']+1})
            self.store.audit(principal,'widget:published',resource_id=identity)
            return result

    def lifecycle(self,principal,identity,action,payload):
        if not payload.confirmed:raise DomainError('forbidden',403)
        with self.store.transaction():
            row=self.get(principal,identity)
            if row['state']=='revoked':raise DomainError('disabled',409)
            changes={'epoch':row['epoch']+1}
            if action=='rollback':
                version=self.store.get('operations_events',principal.tenant_id,payload.version_id or '')
                if version.get('kind')!='widget_version' or version.get('integration_id')!=identity:raise DomainError('not_found',404)
                if version['signature']!=self.signature(principal.tenant_id):raise DomainError('conflict',409)
                draft=self.ux.draft(principal,version['draft_id'])
                if any(test['verdict']!='PASS' for test in self.ux.readiness(principal,draft)['required_tests']):raise DomainError('conflict',409)
                if not all(row['domains'].get(site,{}).get('state')=='verified' for site in version['settings']['origins']):raise DomainError('verification_required',409)
                changes.update(state='published',active_version=version['id'],settings=version['settings'])
            else:changes.update(state='revoked' if action=='revoke' else 'unpublished',active_version=None)
            result=self.store.update('operations_events',principal.tenant_id,identity,changes)
            self.store.audit(principal,'widget:'+action,resource_id=identity)
            return result

    def quota(self,row,category):
        tenant=row['tenant_id'];day=self.clock().date().isoformat()
        for key,maximum in [('widgetquota:'+row['id']+':'+day,row['settings']['daily_'+category]),('widgetquota:tenant:'+day,5000 if category=='messages' else 1000)]:
            counter=self.store.find('operations_events',tenant,key)
            amount=(counter or {}).get(category,0)
            if amount>=maximum:raise DomainError('limit_reached',429)
            if counter:self.store.update('operations_events',tenant,counter['id'],{category:amount+1})
            else:self.store.add('operations_events',tenant,{'kind':'widget_quota',category:1,'day':day},external_key=key)

    def ticket(self,public_id,site):
        with self.store.transaction():
            row=self.resolve(public_id)
            if row['domains'].get(site,{}).get('state')!='verified':raise DomainError('forbidden',403)
            self.quota(row,'sessions')
            secret=secrets.token_urlsafe(32)
            self.store.add('operations_events',row['tenant_id'],{'kind':'widget_ticket','integration_id':row['id'],'epoch':row['epoch'],
                'parent_origin':site,'status':'pending','expires_at':(self.clock()+timedelta(seconds=60)).isoformat()},external_key='widgetticket:'+sha256(secret.encode()).hexdigest())
            version=self.store.get('operations_events',row['tenant_id'],row['active_version'])
            return {'ticket':secret,'default_locale':version['config']['default_locale'],'expires_in':60}

    def redeem(self,public_id,payload):
        with self.store.transaction():
            row=self.resolve(public_id)
            ticket=self.store.find('operations_events',row['tenant_id'],'widgetticket:'+sha256(payload.ticket.encode()).hexdigest())
            if (not ticket or ticket['kind']!='widget_ticket' or ticket['integration_id']!=row['id'] or ticket['epoch']!=row['epoch']
                or ticket['status']!='pending' or ticket['parent_origin']!=payload.parent_origin):raise DomainError('forbidden',403)
            if datetime.fromisoformat(ticket['expires_at'])<=self.clock():raise DomainError('expired',401)
            version=self.store.get('operations_events',row['tenant_id'],row['active_version'])
            if version['signature']!=self.signature(row['tenant_id']):raise DomainError('conflict',409)
            identity=uid();actor=Principal(row['tenant_id'],identity,'operator','widget:'+identity)
            conversation=self.engine.conversation(actor,row['assistant_id'])
            self.store.update('conversations',row['tenant_id'],conversation['id'],{'widget_snapshot_id':version['id'],'widget_integration_id':row['id'],'active_locale':payload.locale})
            self.store.update('conversations',row['tenant_id'],conversation['id'],{'widget_public_id':public_id})
            secret=secrets.token_urlsafe(32);expires=(self.clock()+timedelta(minutes=10)).isoformat()
            self.store.add('operations_events',row['tenant_id'],{'kind':'widget_session','integration_id':row['id'],'epoch':row['epoch'],'version_id':version['id'],
                'conversation_id':conversation['id'],'visitor_id':identity,'status':'active','messages':0,'expires_at':expires,
                'purge_at':(self.clock()+timedelta(days=row['settings']['retention_days'])).isoformat()},external_key='widgetsession:'+sha256(secret.encode()).hexdigest())
            self.store.update('operations_events',row['tenant_id'],ticket['id'],{'status':'used'})
            settings=version['settings']
            return {'session_token':secret,'expires_at':expires,'locale':payload.locale,'greeting':settings['greetings'][payload.locale],
                'privacy_notice':settings['privacy_notices'][payload.locale],'privacy_notices':settings['privacy_notices'],'color':settings['color'],'logo_url':settings['logo_url'],'analytics_enabled':settings.get('analytics_enabled',False),
                'native_booking_enabled':settings['booking_enabled'],
                'voice_available':False,'calendar_state':'UNAVAILABLE' if settings.get('concierge_enabled') else 'MOCK','human_online':False,'concierge_enabled':settings.get('concierge_enabled',False)}

    def session(self,public_id,secret):
        row=self.resolve(public_id)
        session=self.store.find('operations_events',row['tenant_id'],'widgetsession:'+sha256(secret.encode()).hexdigest())
        if (not session or session['kind']!='widget_session' or session['integration_id']!=row['id'] or session['status']!='active'
            or session['epoch']!=row['epoch'] or session['version_id']!=row['active_version']):raise DomainError('unauthorized',401)
        if datetime.fromisoformat(session['expires_at'])<=self.clock():raise DomainError('expired',401)
        version=self.store.get('operations_events',row['tenant_id'],session['version_id'])
        if version['signature']!=self.signature(row['tenant_id']):raise DomainError('conflict',409)
        return row,session,Principal(row['tenant_id'],session['visitor_id'],'operator','widget:'+session['visitor_id'])

    def message(self,public_id,secret,payload):
        with self.store.transaction():
            row,session,actor=self.session(public_id,secret)
            key='widget_'+session['id'].replace('-','')+'_'+payload.event_id
            attempt=self.store.find('operations_events',row['tenant_id'],'widgetattempt:'+key)
            fingerprint=digest(payload.model_dump())
            if attempt and attempt['fingerprint']!=fingerprint:raise DomainError('conflict',409)
            if not attempt:
                if session['messages']>=60:raise DomainError('limit_reached',429)
                self.quota(row,'messages')
                self.store.add('operations_events',row['tenant_id'],{'kind':'widget_attempt','integration_id':row['id'],'fingerprint':fingerprint,'conversation_id':session['conversation_id']},external_key='widgetattempt:'+key)
                self.store.update('operations_events',row['tenant_id'],session['id'],{'messages':session['messages']+1})
        # Admission usage survives a failed runtime action; retrying an identical
        # event does not recharge. The runtime retains its own atomic idempotency.
        with self.store.transaction():
            row,session,actor=self.session(public_id,secret)
            result=self.engine.inbound(actor,session['conversation_id'],Incoming(content=payload.content,event_id=key,locale=payload.locale))
            conversation=self.store.get('conversations',row['tenant_id'],session['conversation_id'])
        try:self.journey.observe(row,session,{**result,'human_requested':bool(conversation.get('human_escalation'))})
        except Exception:
            if getattr(self.store,'operations',None):self.store.operations.observe('journey_projection',row['tenant_id'],error='projection_failed')
        return {'response':result['response'],'locale':result['locale'],'booking_status':result.get('booking_status'),
            'tool_result':(result.get('outcome') or {}).get('code'),'booking_reference':(result.get('outcome') or {}).get('data',{}).get('id') if (result.get('outcome') or {}).get('code')=='appointment_pending' else None,'duplicate':result.get('duplicate',False),
            'human_requested':bool(conversation.get('human_escalation')),'human_online':False,'calendar_state':(result.get('outcome') or {}).get('data',{}).get('state','MOCK')}

    def redact_text_copies(self,tenant,conversation):
        """Erase chat-derived traces without changing durable booking records."""
        self.store.update('conversations',tenant,conversation,{'booking_state':None})
        for message in self.store.list('messages',tenant,conversation):
            self.store.update('messages',tenant,message['id'],{'content':'','attachments':[],'redacted':True})
        for event in self.store.list('provider_events',tenant,conversation):
            self.store.update('provider_events',tenant,event['id'],{'result':{'redacted':True}})
        for table in ('agent_executions','tool_executions','approvals'):
            for trace in self.store.list(table,tenant,conversation):
                changes={'arguments':{},'outcome':{},'result':{},'handoff':{},'redacted':True}
                if table=='approvals' and trace['status']=='pending':changes['status']='cancelled'
                self.store.update(table,tenant,trace['id'],changes)

    def clear(self,public_id,secret):
        row=self.resolve(public_id,published=False,privacy=True)
        session=self.store.find('operations_events',row['tenant_id'],'widgetsession:'+sha256(secret.encode()).hexdigest())
        if not session or session['kind']!='widget_session' or session['integration_id']!=row['id']:raise DomainError('unauthorized',401)
        if session['status'] in ('cleared','purged'):return {'cleared':True,'appointments_deleted':False}
        actor=Principal(row['tenant_id'],session['visitor_id'],'operator','widget:'+session['visitor_id'])
        with self.store.transaction():
            self.journey.withdraw(row['tenant_id'],session['conversation_id'])
            self.redact_text_copies(row['tenant_id'],session['conversation_id'])
            self.store.update('conversations',row['tenant_id'],session['conversation_id'],{'status':'closed'})
            self.store.update('operations_events',row['tenant_id'],session['id'],{'status':'cleared'})
            self.store.audit(actor,'widget:chat_cleared',resource_id=session['conversation_id'])
        return {'cleared':True,'appointments_deleted':False}

    def purge(self):
        """Bounded cleanup of widget text copies, not clinical/business records."""
        self.journey.purge()
        with self.store.lock:
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE json_extract(data,'$.kind')='widget_session' AND json_extract(data,'$.status')!='purged' AND json_extract(data,'$.purge_at')<=? LIMIT 100",(self.clock().isoformat(),)).fetchall()
        for item in rows:
            session=json.loads(item['data'])
            with self.store.transaction():
                self.redact_text_copies(session['tenant_id'],session['conversation_id'])
                self.store.update('conversations',session['tenant_id'],session['conversation_id'],{'status':'closed'})
                self.store.update('operations_events',session['tenant_id'],session['id'],{'status':'purged'})
        return len(rows)


def register_widget(app,store,engine,ux,actor,*,public_origin='',local_sites=(),demo_targets=None):
    service=WidgetService(store,engine,ux,public_origin=public_origin,local_sites=local_sites)
    public_origin=service.public_origin
    if demo_targets:service.fetch_domain=lambda site,identifier,allowed:domain_file(site,identifier,allowed,demo_targets)
    app.state.widget=service
    assets=Path(__file__).resolve().parents[2]/'widget'

    def secret(request):
        authorization=request.headers.get('authorization','')
        if not authorization.startswith('Bearer '):raise DomainError('unauthorized',401)
        return authorization[7:]

    @app.middleware('http')
    async def widget_policy(request,call_next):
        path=request.url.path
        if not path.startswith('/widget/'):return await call_next(request)
        claimed=request.headers.get('origin','')
        admission=path.startswith('/widget/admission/')
        allowed=False
        if admission:
            try:
                row=service.resolve(path.rsplit('/',1)[-1])
                allowed=row['domains'].get(claimed,{}).get('state')=='verified'
            except DomainError:allowed=False
            if not allowed:return JSONResponse({'code':'forbidden'},status_code=403)
            if request.method=='OPTIONS':
                if request.headers.get('access-control-request-method')!='POST':return Response(status_code=403)
                return Response(status_code=204,headers={'Access-Control-Allow-Origin':claimed,'Access-Control-Allow-Methods':'POST','Access-Control-Allow-Headers':'Content-Type','Vary':'Origin','Cache-Control':'no-store'})
        elif request.method=='POST' and claimed!=public_origin:
            return JSONResponse({'code':'forbidden'},status_code=403)
        response=await call_next(request)
        if admission and allowed:
            response.headers['Access-Control-Allow-Origin']=claimed
            response.headers['Vary']='Origin'
        if path.startswith('/widget/frame/') and response.status_code==200 and 'x-frame-options' in response.headers:
            del response.headers['x-frame-options']
        if path.startswith('/widget/assets/') and response.status_code==200:
            response.headers['Cache-Control']='public, max-age=300'
        return response

    @app.get('/api/widgets')
    def integrations(principal:Principal=Depends(actor)):
        principal.require('configure');return service.rows(principal.tenant_id,'widget_integration')

    @app.post('/api/widgets',status_code=201)
    def create(payload:WidgetSettings,principal:Principal=Depends(actor)):return service.configure(principal,payload)

    @app.put('/api/widgets/{identity}')
    def configure(identity:str,payload:WidgetSettings,principal:Principal=Depends(actor)):return service.configure(principal,payload,identity)

    @app.post('/api/widgets/{identity}/challenge')
    def challenge(identity:str,payload:DomainProof,principal:Principal=Depends(actor)):return service.challenge(principal,identity,payload.origin)

    @app.post('/api/widgets/{identity}/verify')
    def verify(identity:str,payload:DomainProof,principal:Principal=Depends(actor)):return service.verify(principal,identity,payload.origin)

    @app.post('/api/widgets/{identity}/publish')
    def publish(identity:str,payload:WidgetPublish,principal:Principal=Depends(actor)):return service.publish(principal,identity,payload)

    @app.post('/api/widgets/{identity}/{action}')
    def lifecycle(identity:str,action:Literal['unpublish','revoke','rollback'],payload:WidgetAction,principal:Principal=Depends(actor)):
        return service.lifecycle(principal,identity,action,payload)

    @app.get('/api/widgets/{identity}/installation')
    def installation(identity:str,principal:Principal=Depends(actor)):
        row=service.get(principal,identity)
        snippet='<script src="'+html.escape(public_origin+'/widget/assets/v1.js',quote=True)+'" data-assistant-id="'+row['public_id']+'" data-locale="auto" async></script>'
        versions=[{key:version.get(key) for key in ('id','created_at','draft_id')} for version in service.rows(principal.tenant_id,'widget_version') if version['integration_id']==identity]
        tickets=[item for item in service.rows(principal.tenant_id,'widget_ticket') if item['integration_id']==identity]
        telemetry={'issued_tickets':len(tickets),'redeemed_tickets':sum(item['status']=='used' for item in tickets),
            'sessions':sum(item['integration_id']==identity for item in service.rows(principal.tenant_id,'widget_session')),
            'unique_message_attempts':sum(item.get('integration_id')==identity for item in service.rows(principal.tenant_id,'widget_attempt')),
            'scope':'all_retained_admissions','browser_installation_proven':False}
        return {'snippet':snippet,'state':row['state'],'domains':row['domains'],'versions':versions,'telemetry':telemetry,'installation_verified':False,'voice_verified':False,'calendar_state':'MOCK'}

    @app.post('/widget/admission/{public_id}')
    def admission(public_id:str,payload:Admission,request:Request):return service.ticket(public_id,request.headers.get('origin',''))

    @app.post('/widget/redeem/{public_id}')
    def redeem(public_id:str,payload:Redeem):return service.redeem(public_id,payload)

    @app.post('/widget/messages/{public_id}')
    def message(public_id:str,payload:WidgetMessage,request:Request):return service.message(public_id,secret(request),payload)

    class AnalyticsConsent(Contract):
        allowed:StrictBool
    @app.post('/widget/analytics-consent/{public_id}')
    def analytics_consent(public_id:str,payload:AnalyticsConsent,request:Request):
        with store.transaction():
            if payload.allowed:
                row,session,_=service.session(public_id,secret(request))
                version=store.get('operations_events',row['tenant_id'],session['version_id'])
                if not version['settings'].get('analytics_enabled'):raise DomainError('forbidden',403)
            else:
                row=service.resolve(public_id,published=False,privacy=True)
                session=store.find('operations_events',row['tenant_id'],'widgetsession:'+sha256(secret(request).encode()).hexdigest())
                if not session or session.get('integration_id')!=row['id'] or session.get('kind')!='widget_session':raise DomainError('unauthorized',401)
            changed=bool(session.get('analytics_allowed'))!=payload.allowed
            session=store.update('operations_events',row['tenant_id'],session['id'],{'analytics_allowed':payload.allowed,'analytics_revision':session.get('analytics_revision',0)+int(changed)})
            if payload.allowed:service.journey.record(row,session,'opted_in_opened','CONSENTED_WIDGET_PRESENT')
            else:service.journey.withdraw(row['tenant_id'],session['conversation_id'])
        return {'allowed':payload.allowed,'retention_days_maximum':7,'raw_content_collected':False}

    @app.get('/widget/history/{public_id}')
    def history(public_id:str,request:Request):
        if request.headers.get('origin','') not in ('',public_origin):raise DomainError('forbidden',403)
        row,session,_=service.session(public_id,secret(request))
        return {'messages':[{**{key:item.get(key) for key in ('id','content','direction','locale','timestamp')},'booking_reference':item.get('metadata',{}).get('appointment_id') if item.get('metadata',{}).get('kind') in ('customer_booking_confirmation','customer_booking_notice') else None,'booking_final':item.get('metadata',{}).get('kind')=='customer_booking_confirmation' or item.get('metadata',{}).get('final') is True,'from_human':bool(item.get('metadata',{}).get('kind')=='human' or str(item.get('correlation_id') or item.get('metadata',{}).get('correlation_id','')).startswith('human:'))} for item in store.list('messages',row['tenant_id'],session['conversation_id'])[-50:]],'human_requested':bool(store.get('conversations',row['tenant_id'],session['conversation_id']).get('human_escalation')),'human_online':False}

    @app.post('/widget/clear/{public_id}')
    def clear(public_id:str,payload:WidgetAction,request:Request):
        if not payload.confirmed:raise DomainError('forbidden',403)
        return service.clear(public_id,secret(request))

    @app.get('/widget/assets/{name}')
    def asset(name:Literal['v1.js','loader.css','frame.js','frame.css','catalog.js','concierge.js','concierge-labels.js','manage.js']):
        path=assets/name
        if not path.is_file():raise DomainError('not_found',404)
        content=path.read_bytes()
        return Response(content,media_type='text/css' if name.endswith('.css') else 'text/javascript',headers={'ETag':'"'+sha256(content).hexdigest()+'"'})

    @app.get('/widget/brand/{public_id}.css')
    def brand(public_id:str):
        row=service.resolve(public_id);version=store.get('operations_events',row['tenant_id'],row['active_version'])
        color=version['settings']['color']
        channels=[int(color[index:index+2],16)/255 for index in (1,3,5)]
        linear=[value/12.92 if value<=.04045 else ((value+.055)/1.055)**2.4 for value in channels]
        luminance=sum(value*weight for value,weight in zip(linear,(.2126,.7152,.0722)))
        text='#ffffff' if 1.05/(luminance+.05)>=(luminance+.05)/.05 else '#000000'
        appearance=version['settings'].get('appearance','default')
        profile=';--surface:#080f1c;--panel:#0d1624;--bubble:#112232;--reply:#123c49;--text:#edf2f7;--border:#2b3a4d;--error:#ffaaaa;--font:"Segoe UI",Inter,Arial,sans-serif' if appearance=='ontelyx-dark' else ''
        return Response(':root{--brand:'+color+';--brand-text:'+text+profile+'}',media_type='text/css')

    @app.get('/widget/frame/{public_id}')
    def frame(public_id:str,parent_origin:str,locale:Literal['auto','bg-BG','en-US']='auto'):
        row=service.resolve(public_id)
        if row['domains'].get(parent_origin,{}).get('state')!='verified':raise DomainError('forbidden',403)
        content=(assets/'frame.html').read_text(encoding='utf-8').replace('{{PUBLIC_ID}}',html.escape(public_id,quote=True)).replace('{{PARENT_ORIGIN}}',html.escape(parent_origin,quote=True)).replace('{{LOCALE}}',locale)
        policy="default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' https:; base-uri 'none'; form-action 'none'; frame-ancestors "+parent_origin
        return HTMLResponse(content,headers={'Content-Security-Policy':policy,'Permissions-Policy':'microphone=(), camera=(), geolocation=()','Referrer-Policy':'no-referrer'})
    return service
