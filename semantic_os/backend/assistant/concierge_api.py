"""v1 public actions are scoped to widget capabilities; Google admin is separate."""
from hashlib import sha256
from datetime import date
import json
from typing import Literal
from fastapi import Depends,Request,Response,Query
from fastapi.responses import HTMLResponse
from pydantic import Field
from .domain import Contract,DomainError,Principal,Locale
from .google_workspace import GoogleClientConfig
from .concierge import ConciergePolicy,SCHEMAS
from .store import uid

class ConciergeAction(Contract):
    tool:Literal['ConciergeAvailability','ConciergeBooking','ConciergeManage','ConciergeRequest']
    arguments:dict
    event_id:str=Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    locale:Locale

class EmailVerification(Contract):
    email:str=Field(default='',max_length=250)
    verification_id:str=Field(default='',max_length=100)
    code:str=Field(default='',max_length=6)
    locale:Locale

class OwnedAction(Contract):
    token:str=Field(min_length=50,max_length=2000)
    action:Literal['details','availability','cancel','reschedule']
    day:date|None=None
    starts_at:str|None=None
    confirmed:bool=False
    event_id:str=Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    locale:Locale

class RecoverManagement(Contract):
    booking_id:str=Field(max_length=100)
    email:str=Field(max_length=250)
    verification_id:str=Field(max_length=100)
    locale:Locale

def register_concierge(app,actor):
    service,google,widget=app.state.concierge,app.state.google,app.state.widget
    service.widget=widget

    @app.get('/api/google')
    def google_status(principal:Principal=Depends(actor)):return google.status(principal)

    @app.post('/api/google/config')
    def client_config(payload:GoogleClientConfig,principal:Principal=Depends(actor)):return google.configure(principal,payload)

    @app.post('/api/google/oauth/{kind}')
    def oauth_start(kind:Literal['calendar','gmail'],request:Request,response:Response,principal:Principal=Depends(actor)):
        url,binding=google.start(principal,kind,request.headers.get('x-ui-locale','en-US'))
        response.set_cookie('ontelyx-google-'+kind,binding,max_age=600,httponly=True,secure=not google.development,samesite='lax',path='/')
        return {'authorize_url':url}

    @app.get('/api/google/oauth/callback')
    def oauth_callback(request:Request,state:str=Query(default='',max_length=150),code:str=Query(default='',max_length=4096),error:str|None=None):
        if error:raise DomainError('oauth_denied',403)
        result=google.callback(state,code,{kind:request.cookies.get('ontelyx-google-'+kind,'') for kind in ('calendar','gmail')})
        bg=result['locale']=='bg-BG';message='Връзката с Google е разрешена.' if bg else 'Google connection authorized.';label='Обратно към настройките' if bg else 'Return to settings'
        response=HTMLResponse('<!doctype html><html lang="'+result['locale']+'"><meta charset="utf-8"><title>Google Workspace</title><p>'+message+'</p><a href="/google">'+label+'</a></html>',headers={'Referrer-Policy':'no-referrer','Content-Security-Policy':"default-src 'none'; base-uri 'none'; frame-ancestors 'none'"})
        response.delete_cookie('ontelyx-google-'+result['connection'],path='/')
        return response

    @app.post('/api/google/revoke/{kind}')
    def revoke(kind:Literal['calendar','gmail'],principal:Principal=Depends(actor)):return google.revoke(principal,kind)

    @app.get('/api/concierge/policy')
    def get_policy(principal:Principal=Depends(actor)):
        principal.require('configure')
        try:return service.policy(principal.tenant_id).model_dump(mode='json')
        except DomainError:return ConciergePolicy().model_dump(mode='json')

    @app.put('/api/concierge/policy')
    def configure_policy(payload:ConciergePolicy,principal:Principal=Depends(actor)):return service.configure(principal,payload)

    @app.get('/api/concierge/requests')
    def requests(principal:Principal=Depends(actor)):
        principal.require('configure');return service.rows(principal.tenant_id,'concierge_request')

    @app.get('/api/concierge/email-jobs')
    def email_jobs(principal:Principal=Depends(actor)):
        principal.require('configure')
        return [{key:row.get(key) for key in ('id','status','attempts','due_at','error_code','google_message_id')} for row in service.store.list('jobs',principal.tenant_id) if row.get('kind')=='concierge_email']

    @app.post('/api/concierge/email-jobs/{identity}/retry')
    def retry_email(identity:str,principal:Principal=Depends(actor)):
        principal.require('configure');row=service.store.get('jobs',principal.tenant_id,identity)
        if row.get('kind')!='concierge_email' or row['status']!='blocked' or row.get('error_code') not in ('google_not_connected','provider_rate_limited','provider_rejected'):raise DomainError('conflict',409)
        return service.store.update('jobs',principal.tenant_id,identity,{'status':'pending','due_at':service.clock().isoformat()})

    def visitor(request,public_id):
        bearer=request.headers.get('authorization','')
        if not bearer.startswith('Bearer '):raise DomainError('unauthorized',401)
        row,session,principal=widget.session(public_id,bearer[7:])
        if service.store.entitlements:service.store.entitlements.access(principal.tenant_id)
        version=widget.store.get('operations_events',row['tenant_id'],session['version_id'])
        if not version['settings'].get('concierge_enabled'):raise DomainError('concierge_unavailable',503)
        conversation=widget.store.get('conversations',principal.tenant_id,session['conversation_id'])
        assistant=service.engine.configuration(principal,conversation)
        return row,session,principal,conversation,assistant

    @app.get('/widget/v1/concierge/{public_id}')
    def capabilities(public_id:str,request:Request):
        row,_,principal,_,_=visitor(request,public_id)
        policy=service.policy(principal.tenant_id)
        try:service.ready(principal.tenant_id,True);booking=True
        except DomainError:booking=False
        return {'schema_version':'1.0','booking_available':booking,'timezone':'Europe/Sofia','opens':policy.opens,'closes':policy.closes,'duration_minutes':policy.duration_minutes,'buffer_minutes':policy.buffer_minutes,'ends_on':policy.ends_on.isoformat(),'voice_available':False}

    @app.post('/widget/v1/actions/{public_id}')
    def action(public_id:str,payload:ConciergeAction,request:Request):
        row,session,principal,conversation,assistant=visitor(request,public_id)
        arguments=service.engine.booking.receptionist.prepare_action(payload.tool,payload.arguments,payload.locale,service.engine.tools)
        fingerprint=sha256(payload.model_dump_json().encode()).hexdigest();key='concierge_public_'+session['id'].replace('-','')+'_'+payload.event_id
        with service.store.transaction():
            previous=service.store.find('operations_events',principal.tenant_id,'concierge-public:'+key)
            if previous and previous['fingerprint']!=fingerprint:raise DomainError('conflict',409)
            if not previous:
                if session['messages']>=60:raise DomainError('limit_reached',429)
                widget.quota(row,'messages')
                service.store.update('operations_events',principal.tenant_id,session['id'],{'messages':session['messages']+1})
                service.store.add('operations_events',principal.tenant_id,{'kind':'concierge_public_attempt','fingerprint':fingerprint,'conversation_id':conversation['id']},external_key='concierge-public:'+key)
        # Reauthenticate after admission charging; remote writes happen outside DB transactions.
        row,session,principal,conversation,assistant=visitor(request,public_id)
        conversation=service.store.update('conversations',principal.tenant_id,conversation['id'],{'active_locale':payload.locale})
        correlation=uid()
        receptionist=service.store.get('agents',principal.tenant_id,'receptionist')
        if not receptionist['enabled'] or 'receptionist' not in assistant['assigned_agents']:raise DomainError('disabled',409)
        handed=service.engine.booking.executor.handoff(principal,assistant,conversation,payload.tool,arguments,payload.locale,correlation)
        outcome=service.engine.tools.execute(principal,assistant,conversation,payload.tool,handed,key=key,correlation_id=correlation,approved=payload.tool=='ConciergeAvailability' or handed.get('consent') is True)
        # Store a concise visitor-visible outcome in the existing conversation.
        text=('Заявката е обработена.' if payload.locale=='bg-BG' else 'Your request was processed.')
        cached=service.store.find('provider_events',principal.tenant_id,'concierge-response:'+key)
        if not cached:
            service.engine.dispatch(principal,assistant,conversation,text,payload.locale,correlation)
            service.store.add('provider_events',principal.tenant_id,{'conversation_id':conversation['id'],'result':{'status':outcome['data'].get('status'),'locale':payload.locale}},external_key='concierge-response:'+key)
        return {'data':outcome['data'],'locale':payload.locale,'correlation_id':correlation,'duplicate':bool(previous)}

    @app.post('/widget/v1/verify-email/{public_id}')
    def email_verify(public_id:str,payload:EmailVerification,request:Request):
        row,session,principal,conversation,assistant=visitor(request,public_id)
        if 'ConciergeBooking' not in assistant['allowed_tools'] and 'ConciergeRequest' not in assistant['allowed_tools']:raise DomainError('tool_denied',403)
        conversation=service.store.update('conversations',principal.tenant_id,conversation['id'],{'active_locale':payload.locale})
        if payload.verification_id:return service.confirm_email(principal,conversation,payload.verification_id,payload.code)
        return service.verify_email(principal,conversation,payload.email)

    @app.get('/widget/manage/{public_id}')
    def management_page(public_id:str):
        widget.resolve(public_id)
        from pathlib import Path
        content=(Path(__file__).resolve().parents[2]/'widget/manage.html').read_text(encoding='utf-8').replace('{{PUBLIC_ID}}',public_id)
        return HTMLResponse(content,headers={'Content-Security-Policy':"default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'",'Referrer-Policy':'no-referrer'})

    @app.post('/widget/v1/recover/{public_id}')
    def recover(public_id:str,payload:RecoverManagement,request:Request):
        _,_,principal,conversation,_=visitor(request,public_id)
        return service.recover_management(principal,conversation,payload.booking_id,payload.email,payload.verification_id)

    @app.post('/widget/v1/manage/{public_id}')
    def manage(public_id:str,payload:OwnedAction):
        row=widget.resolve(public_id);booking=service.owned(row['tenant_id'],payload.token,stale=True)
        if booking['public_id']!=public_id:raise DomainError('ownership_required',403)
        if payload.action=='details':
            service.owned(row['tenant_id'],payload.token)
            return {key:booking[key] for key in ('starts_at','ends_at','status','locale')}
        if payload.action=='availability':
            service.owned(row['tenant_id'],payload.token)
            if not payload.day:raise DomainError('invalid_input',422)
            return service.slots(row['tenant_id'],payload.day,exclude=booking)
        if not payload.confirmed:raise DomainError('forbidden',403)
        args=service.engine.tools.validate('ConciergeManage',{'action':payload.action,'management_token':payload.token,'starts_at':payload.starts_at,'consent':True})
        cache=service.store.find('operations_events',row['tenant_id'],'concierge-action:'+booking['conversation_id']+':management_'+payload.event_id)
        fingerprint=sha256(json.dumps({'name':'ConciergeManage','args':args},sort_keys=True).encode()).hexdigest()
        if cache and cache['status']=='completed' and cache['fingerprint']==fingerprint:return {'data':cache['outcome']['data'],'locale':payload.locale,'duplicate':True}
        service.owned(row['tenant_id'],payload.token)
        from .domain import Principal
        principal=Principal(row['tenant_id'],'verified-booking-owner','operator','verified-booking-owner')
        conversation=service.store.get('conversations',row['tenant_id'],booking['conversation_id']);assistant=service.engine.configuration(principal,conversation)
        conversation=service.store.update('conversations',row['tenant_id'],conversation['id'],{'active_locale':payload.locale})
        handed=service.engine.booking.executor.handoff(principal,assistant,conversation,'ConciergeManage',args,payload.locale,uid())
        result=service.engine.tools.execute(principal,assistant,conversation,'ConciergeManage',handed,key='management_'+payload.event_id,correlation_id=uid(),approved=True)
        return {'data':result['data'],'locale':payload.locale}
