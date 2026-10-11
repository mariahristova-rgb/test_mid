"""Owner-authorized Google connections. Tokens and endpoints never come from visitors."""
import base64
from datetime import datetime,timedelta
from hashlib import sha256
import json
import secrets
from threading import RLock
from typing import Literal
from urllib.parse import urlencode,urlsplit,quote
import httpx
from pydantic import Field,SecretStr,field_validator
from .domain import Contract,DomainError,Principal

ACCOUNT='mariya.manolova92@gmail.com'
SCOPES={'calendar':['https://www.googleapis.com/auth/calendar.events.owned','https://www.googleapis.com/auth/calendar.freebusy','https://www.googleapis.com/auth/calendar.calendarlist.readonly'],
        'gmail':['https://www.googleapis.com/auth/gmail.send']}

class GoogleClientConfig(Contract):
    kind:Literal['calendar','gmail']
    client_id:str=Field(min_length=10,max_length=300)
    client_secret:SecretStr
    redirect_uri:str=Field(max_length=500)
    expected_account:str=ACCOUNT
    @field_validator('client_id')
    @classmethod
    def client(cls,value):
        if not value.endswith('.apps.googleusercontent.com'):raise ValueError('invalid client')
        return value

class GoogleWorkspace:
    def __init__(self,store,secret_store,clock,*,transport=None,development=False):
        self.store,self.secrets,self.clock=store,secret_store,clock
        self.transport,self.development=transport,development
        self.lock=RLock()

    def http(self,method,url,**kwargs):
        try:
            with httpx.Client(transport=self.transport,timeout=15,follow_redirects=False) as client:
                response=client.request(method,url,**kwargs)
            if len(response.content)>1_000_000:raise DomainError('provider_error',502)
            return response
        except httpx.TimeoutException:raise DomainError('delivery_unknown',504) from None
        except httpx.HTTPError:raise DomainError('provider_error',502) from None

    def row(self,tenant,kind):return self.store.find('operations_events',tenant,'google:'+kind)

    def status(self,principal):
        principal.require('configure')
        return [{key:row.get(key) for key in ('kind','connection','state','account','expected_account','redirect_uri','client_id')} for kind in SCOPES if (row:=self.row(principal.tenant_id,kind))]

    def configure(self,principal,payload):
        principal.require('configure');uri=urlsplit(payload.redirect_uri)
        if not uri.hostname or uri.username or uri.password or uri.query or uri.fragment or uri.path.split('/')[-3:]!=['google','oauth','callback']:raise DomainError('invalid_input',422)
        if uri.scheme!='https' and not(self.development and uri.scheme=='http' and uri.hostname in ('127.0.0.1','localhost')):raise DomainError('invalid_input',422)
        if payload.expected_account.casefold()!=ACCOUNT:raise DomainError('forbidden',403)
        with self.store.transaction():
            self.secrets.put(principal.tenant_id,'google:'+payload.kind+':client_secret',payload.client_secret.get_secret_value(),principal)
            data={'kind':'google_connection','connection':payload.kind,'client_id':payload.client_id,'redirect_uri':payload.redirect_uri,
                'expected_account':ACCOUNT,'state':'disconnected','account':None}
            old=self.row(principal.tenant_id,payload.kind)
            if old:self.store.update('operations_events',principal.tenant_id,old['id'],data)
            else:self.store.add('operations_events',principal.tenant_id,data,external_key='google:'+payload.kind)
            # Old refresh material cannot be reused under new client configuration.
            self.secrets.put(principal.tenant_id,'google:'+payload.kind+':tokens','{}',principal)
            self.store.audit(principal,'google:client_configured')
        return {'state':'disconnected','connection':payload.kind}

    def start(self,principal,kind,locale='en-US'):
        principal.require('configure');row=self.row(principal.tenant_id,kind)
        if not row:raise DomainError('unconfigured',503)
        state=secrets.token_urlsafe(32);binding=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        with self.store.transaction():
            event=self.store.add('operations_events',principal.tenant_id,{'kind':'google_oauth_state','connection':kind,'user_id':principal.user_id,'subject':principal.subject,'locale':locale if locale in ('bg-BG','en-US') else 'en-US',
                'binding_hash':sha256(binding.encode()).hexdigest(),'client_hash':sha256(json.dumps(row,sort_keys=True).encode()).hexdigest(),'status':'pending','expires_at':(self.clock()+timedelta(minutes=10)).isoformat()},external_key='google-state:'+sha256(state.encode()).hexdigest())
            self.secrets.put(principal.tenant_id,'google:verifier:'+event['id'],verifier,principal)
        url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':row['client_id'],'redirect_uri':row['redirect_uri'],'response_type':'code','scope':' '.join(['openid','email',*SCOPES[kind]]),
            'access_type':'offline','prompt':'consent','include_granted_scopes':'true','login_hint':ACCOUNT,'state':state,'code_challenge':base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip('='),'code_challenge_method':'S256'})
        return url,binding

    def callback(self,state,code,bindings):
        with self.store.transaction():
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE external_key=? AND json_extract(data,'$.kind')='google_oauth_state'",('google-state:'+sha256(state.encode()).hexdigest(),)).fetchall()
            if len(rows)!=1:raise DomainError('unauthorized',401)
            event=json.loads(rows[0]['data']);kind=event['connection'];binding=bindings.get(kind,'')
            if event['status']!='pending' or datetime.fromisoformat(event['expires_at'])<=self.clock() or sha256(binding.encode()).hexdigest()!=event['binding_hash']:raise DomainError('unauthorized',401)
            principal=self.store.principal(event['subject'],event['tenant_id']);principal.require('configure')
            row=self.row(principal.tenant_id,kind)
            if sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()!=event['client_hash']:raise DomainError('conflict',409)
            self.store.update('operations_events',principal.tenant_id,event['id'],{'status':'consumed'})
        response=self.http('POST','https://oauth2.googleapis.com/token',data={'grant_type':'authorization_code','code':code,'client_id':row['client_id'],'redirect_uri':row['redirect_uri'],
            'client_secret':self.secrets.get(principal.tenant_id,'google:'+kind+':client_secret',principal),'code_verifier':self.secrets.get(principal.tenant_id,'google:verifier:'+event['id'],principal)})
        if response.status_code!=200:raise DomainError('oauth_denied',403)
        tokens=response.json();granted=set(tokens.get('scope','').split())
        if not set(SCOPES[kind])<=granted or not tokens.get('refresh_token') or not tokens.get('access_token'):raise DomainError('oauth_denied',403)
        identity=self.http('GET','https://openidconnect.googleapis.com/v1/userinfo',headers={'Authorization':'Bearer '+tokens['access_token']})
        if identity.status_code!=200:raise DomainError('oauth_denied',403)
        account=identity.json()
        if account.get('email_verified') is not True or account.get('email','').casefold()!=row['expected_account']:raise DomainError('oauth_account_mismatch',403)
        tokens['expires_at']=(self.clock()+timedelta(seconds=min(int(tokens.get('expires_in',3600)),3600))).isoformat()
        with self.store.transaction():
            if self.row(principal.tenant_id,kind)!=row:raise DomainError('conflict',409)
            self.secrets.put(principal.tenant_id,'google:'+kind+':tokens',json.dumps(tokens),principal)
            self.store.update('operations_events',principal.tenant_id,row['id'],{'state':'connected','account':ACCOUNT})
            self.store.audit(principal,'google:connected')
        return {'connection':kind,'state':'connected','account':ACCOUNT,'locale':event.get('locale','en-US')}

    def token(self,tenant,kind):
        with self.lock:
            row=self.row(tenant,kind)
            if not row or row['state']!='connected':raise DomainError('google_not_connected',503)
            tokens=json.loads(self.secrets.get(tenant,'google:'+kind+':tokens'))
            if datetime.fromisoformat(tokens['expires_at'])>self.clock()+timedelta(seconds=60):return tokens['access_token']
            response=self.http('POST','https://oauth2.googleapis.com/token',data={'grant_type':'refresh_token','refresh_token':tokens['refresh_token'],
                'client_id':row['client_id'],'client_secret':self.secrets.get(tenant,'google:'+kind+':client_secret')})
            if response.status_code!=200:
                self.store.update('operations_events',tenant,row['id'],{'state':'reconnect_required'})
                raise DomainError('google_not_connected',503)
            fresh=response.json()
            if not fresh.get('access_token'):raise DomainError('provider_error',502)
            tokens.update(fresh);tokens['expires_at']=(self.clock()+timedelta(seconds=min(int(fresh.get('expires_in',3600)),3600))).isoformat()
            self.secrets.put(tenant,'google:'+kind+':tokens',json.dumps(tokens))
            return tokens['access_token']

    def call(self,tenant,kind,method,path,**kwargs):
        bases={'calendar':'https://www.googleapis.com/calendar/v3/','gmail':'https://gmail.googleapis.com/gmail/v1/'}
        if path.startswith('/') or '://' in path:raise DomainError('invalid_input',422)
        headers={**kwargs.pop('headers',{}),'Authorization':'Bearer '+self.token(tenant,kind)}
        response=self.http(method,bases[kind]+path,headers=headers,**kwargs)
        if response.status_code==401:
            row=self.row(tenant,kind);self.store.update('operations_events',tenant,row['id'],{'state':'reconnect_required'})
            raise DomainError('google_not_connected',503)
        if response.status_code==412:raise DomainError('stale_event',409)
        if kind=='gmail' and response.status_code==429:raise DomainError('provider_rate_limited',429)
        if kind=='gmail' and response.status_code in (400,403):raise DomainError('provider_rejected',502)
        if response.status_code not in (200,201,204,404,409):raise DomainError('provider_error',502)
        return response

    def revoke(self,principal,kind):
        principal.require('configure');row=self.row(principal.tenant_id,kind)
        if not row:raise DomainError('not_found',404)
        tokens=json.loads(self.secrets.get(principal.tenant_id,'google:'+kind+':tokens'))
        try:
            token=tokens.get('refresh_token') or tokens.get('access_token')
            if token:self.http('POST','https://oauth2.googleapis.com/revoke',data={'token':token})
        finally:
            self.secrets.put(principal.tenant_id,'google:'+kind+':tokens','{}',principal)
            self.store.update('operations_events',principal.tenant_id,row['id'],{'state':'revoked'})
        return {'state':'revoked'}
