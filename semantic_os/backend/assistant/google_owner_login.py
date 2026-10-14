"""Additive owner-only Google OIDC adapter for the existing identity/membership layer."""
import base64
from datetime import timedelta
from hashlib import sha256
import hmac
import json
import secrets
from urllib.parse import urlencode,urlsplit
import httpx
import jwt
from fastapi import Request,Response
from fastapi.responses import RedirectResponse
from pydantic import Field
from .domain import Contract,DomainError,Principal
from .google_workspace import ACCOUNT
from ..api.auth0_auth import AuthenticatedSubject

class LoginTicket(Contract):
    ticket:str=Field(min_length=32,max_length=100)

class GoogleOwnerVerifier:
    def __init__(self,client_id,*,jwks=None):
        if not client_id.endswith('.apps.googleusercontent.com'):raise RuntimeError('A Google OAuth web client is required')
        self.client_id=client_id
        self.jwks=jwks or jwt.PyJWKClient('https://www.googleapis.com/oauth2/v3/certs',timeout=10)
    def claims(self,token):
        try:
            key=self.jwks.get_signing_key_from_jwt(token).key
            claims=jwt.decode(token,key,algorithms=['RS256'],audience=self.client_id,issuer=['https://accounts.google.com','accounts.google.com'],
                options={'require':['exp','iat','sub','email','email_verified'],'strict_aud':True},leeway=30)
            if claims['email_verified'] is not True or not isinstance(claims['email'],str) or claims['email'].casefold()!=ACCOUNT:raise DomainError('forbidden',403)
            if not isinstance(claims['sub'],str) or not claims['sub'] or len(claims['sub'])>200:raise DomainError('unauthorized',401)
            return claims
        except DomainError:raise
        except (jwt.PyJWTError,ValueError,TypeError,KeyError):raise DomainError('unauthorized',401) from None
    def verify(self,authorization):
        scheme,_,token=(authorization or '').partition(' ')
        if scheme.casefold()!='bearer' or not token or len(token)>16000:raise DomainError('unauthorized',401)
        claims=self.claims(token)
        return AuthenticatedSubject('GOOGLE','google:'+claims['sub'])

class GoogleOwnerLogin:
    def __init__(self,store,secret_store,clock,verifier,client_secret,tenant,redirect_uri,*,transport=None):
        uri=urlsplit(redirect_uri)
        if uri.scheme!='https' or not uri.hostname or uri.username or uri.password or uri.query or uri.fragment or not uri.path.endswith('/api/auth/google/callback'):raise RuntimeError('Exact HTTPS owner callback required')
        self.store,self.secrets,self.clock,self.verifier=store,secret_store,clock,verifier
        self.client_secret,self.tenant,self.redirect_uri,self.transport=client_secret,tenant,redirect_uri,transport
        self.return_origin=uri.scheme+'://'+uri.netloc
    def start(self,locale):
        self.store.tenant(self.tenant)
        state=secrets.token_urlsafe(32);binding=secrets.token_urlsafe(32);nonce=secrets.token_urlsafe(32);verifier=secrets.token_urlsafe(48)
        row=self.store.add('operations_events',self.tenant,{'kind':'owner_login_state','status':'pending','binding_hash':sha256(binding.encode()).hexdigest(),
            'expires_at':(self.clock()+timedelta(minutes=10)).isoformat(),'locale':locale if locale in ('bg-BG','en-US') else 'en-US'},external_key='owner-login:'+sha256(state.encode()).hexdigest())
        self.secrets.put(self.tenant,'owner-login:'+row['id'],json.dumps({'nonce':nonce,'verifier':verifier}))
        challenge=base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip('=')
        url='https://accounts.google.com/o/oauth2/v2/auth?'+urlencode({'client_id':self.verifier.client_id,'redirect_uri':self.redirect_uri,'response_type':'code','scope':'openid email',
            'state':state,'nonce':nonce,'code_challenge':challenge,'code_challenge_method':'S256','prompt':'select_account'})
        return url,binding
    def callback(self,state,code,binding):
        with self.store.transaction():
            row=self.store.find('operations_events',self.tenant,'owner-login:'+sha256(state.encode()).hexdigest())
            if not row or row['kind']!='owner_login_state' or row['status']!='pending' or row['expires_at']<=self.clock().isoformat() or not hmac.compare_digest(row['binding_hash'],sha256(binding.encode()).hexdigest()):raise DomainError('oauth_state_invalid',403)
            material=json.loads(self.secrets.get(self.tenant,'owner-login:'+row['id']))
            self.store.update('operations_events',self.tenant,row['id'],{'status':'used'})
            self.secrets.put(self.tenant,'owner-login:'+row['id'],'')
        try:
            with httpx.Client(transport=self.transport,timeout=15,follow_redirects=False) as client:
                response=client.post('https://oauth2.googleapis.com/token',data={'grant_type':'authorization_code','client_id':self.verifier.client_id,'client_secret':self.client_secret,
                    'redirect_uri':self.redirect_uri,'code':code,'code_verifier':material['verifier']})
            if response.status_code!=200 or len(response.content)>100000:raise DomainError('unauthorized',401)
            token=response.json().get('id_token','');claims=self.verifier.claims(token)
            if not hmac.compare_digest(str(claims.get('nonce','')),material['nonce']):raise DomainError('oauth_state_invalid',403)
        except httpx.HTTPError:raise DomainError('provider_error',502) from None
        subject='google:'+claims['sub']
        with self.store.transaction():
            member=self.store.find('users',self.tenant,subject)
            if member and not member['enabled']:raise DomainError('forbidden',403)
            if not member:member=self.store.add('users',self.tenant,{'subject':subject,'role':'admin','enabled':True,'preferred_locale':row['locale']},external_key=subject)
            actor=self.store.principal(subject,self.tenant)
            ticket=secrets.token_urlsafe(32)
            issued=self.store.add('operations_events',self.tenant,{'kind':'owner_login_ticket','status':'pending','binding_hash':row['binding_hash'],'expires_at':(self.clock()+timedelta(seconds=60)).isoformat(),'subject':subject},external_key='owner-ticket:'+sha256(ticket.encode()).hexdigest())
            self.secrets.put(self.tenant,'owner-ticket:'+issued['id'],token)
            self.store.audit(actor,'auth:google_owner_authenticated',resource_id=member['id'])
        return ticket
    def redeem(self,ticket,binding):
        with self.store.transaction():
            row=self.store.find('operations_events',self.tenant,'owner-ticket:'+sha256(ticket.encode()).hexdigest())
            if not row or row['kind']!='owner_login_ticket' or row['status']!='pending' or row['expires_at']<=self.clock().isoformat() or not hmac.compare_digest(row['binding_hash'],sha256(binding.encode()).hexdigest()):raise DomainError('oauth_state_invalid',403)
            actor=self.store.principal(row['subject'],self.tenant)
            token=self.secrets.get(self.tenant,'owner-ticket:'+row['id'])
            if self.verifier.verify('Bearer '+token).subject!=actor.subject:raise DomainError('forbidden',403)
            self.store.update('operations_events',self.tenant,row['id'],{'status':'used'})
            self.secrets.put(self.tenant,'owner-ticket:'+row['id'],'')
            return {'access_token':token,'tenant_id':self.tenant}
    def purge(self):
        rows=[row for row in self.store.list('operations_events',self.tenant) if row.get('kind') in ('owner_login_ticket','owner_login_state') and row.get('expires_at','')<=self.clock().isoformat() and not row.get('redacted')][:100]
        for row in rows:
            prefix='owner-ticket:' if row['kind']=='owner_login_ticket' else 'owner-login:'
            self.secrets.put(self.tenant,prefix+row['id'],'')
            self.store.update('operations_events',self.tenant,row['id'],{'redacted':True})
        return len(rows)

def register_google_owner_login(app,service):
    @app.post('/api/auth/google/start')
    def start(request:Request,response:Response):
        url,binding=service.start(request.headers.get('x-ui-locale','en-US'))
        response.set_cookie('owner-google-binding',binding,max_age=600,httponly=True,secure=True,samesite='lax',path='/')
        response.headers['Cache-Control']='no-store'
        return {'authorize_url':url}
    @app.get('/api/auth/google/callback')
    def callback(request:Request,state:str='',code:str='',error:str=''):
        try:
            if error or len(state)>150 or len(code)>4096:raise DomainError('oauth_denied',403)
            ticket=service.callback(state,code,request.cookies.get('owner-google-binding',''))
            target=service.return_origin+'/#owner_ticket='+ticket
        except DomainError:
            target=service.return_origin+'/?owner_error=true'
        return RedirectResponse(target,status_code=303,headers={'Referrer-Policy':'no-referrer','Cache-Control':'no-store'})
    @app.post('/api/auth/google/redeem')
    def redeem(payload:LoginTicket,request:Request,response:Response):
        result=service.redeem(payload.ticket,request.cookies.get('owner-google-binding',''))
        response.delete_cookie('owner-google-binding',path='/');response.headers['Cache-Control']='no-store'
        return result
