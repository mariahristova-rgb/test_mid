"""Tenant/user-bound OAuth protocol fixtures. Real app configuration is intentionally absent."""
import base64
from datetime import timedelta
from hashlib import sha256
import hmac
import json
import secrets
from threading import RLock
from urllib.parse import urlencode
from .connector_adapters import PROFILES, required_scopes
from .domain import DomainError

class ConnectorOAuth:
    def __init__(self,service,http,clock):self.service,self.http,self.clock,self.lock=service,http,clock,RLock()
    def start(self,principal,identity,revision):
        self.service.guard(principal)
        with self.service.store.transaction():
            row=self.service.row(principal,identity)
            if row['revision']!=revision:raise DomainError('conflict',409)
            if row.get('failure_code')=='delivery_unknown':raise DomainError('delivery_unknown',409)
            if self.service.store.entitlements:self.service.store.entitlements.check_connector(principal.tenant_id,row['provider'])
            state,binding,verifier=secrets.token_urlsafe(32),secrets.token_urlsafe(32),secrets.token_urlsafe(48)
            event=self.service.store.add('operations_events',principal.tenant_id,{
                'kind':'connector_oauth_fixture','connection_id':identity,'revision':revision,
                'subject':principal.subject,'user_id':principal.user_id,'binding_hash':sha256(binding.encode()).hexdigest(),
                'expires_at':(self.clock()+timedelta(minutes=10)).isoformat(),'state':'pending'},external_key='connector-oauth:'+sha256(state.encode()).hexdigest())
            self.service.secrets.put(principal.tenant_id,'connector:verifier:'+event['id'],verifier,principal)
        profile=PROFILES[row['provider']]
        params={'client_id':'fixture-'+row['provider'],'response_type':'code','redirect_uri':self.redirect(row['provider']),
                'scope':' '.join(required_scopes(row['provider'],row['actions'])),'state':state}
        if profile['pkce']:params.update(code_challenge_method='S256',code_challenge=base64.urlsafe_b64encode(sha256(verifier.encode()).digest()).decode().rstrip('='))
        if row['provider']=='google':params.update(access_type='offline',prompt='consent')
        # Display/test only; clients must never navigate this fake application URL.
        return {'state':state,'binding':binding,'authorization_preview':profile['authorize']+'?'+urlencode(params),'simulation':True}
    @staticmethod
    def redirect(provider):return 'http://127.0.0.1:8019/backend/api/connectors/oauth/'+provider+'/fixture-callback'
    def complete(self,principal,identity,state,binding,code):
        self.service.guard(principal)
        if code!='fixture-code':raise DomainError('invalid_input',422)
        with self.service.store.transaction():
            event=self.service.store.find('operations_events',principal.tenant_id,'connector-oauth:'+sha256(state.encode()).hexdigest())
            if not event or event['kind']!='connector_oauth_fixture' or event['connection_id']!=identity or event['subject']!=principal.subject or event['user_id']!=principal.user_id or event['state']!='pending' or self.clock().isoformat()>=event['expires_at'] or not hmac.compare_digest(event['binding_hash'],sha256(binding.encode()).hexdigest()):raise DomainError('unauthorized',401)
            row=self.service.row(principal,identity)
            if row['revision']!=event['revision']:raise DomainError('conflict',409)
            if self.service.store.entitlements:self.service.store.entitlements.check_connector(principal.tenant_id,row['provider'])
            self.service.store.update('operations_events',principal.tenant_id,event['id'],{'state':'consumed'})
        provider=row['provider'];profile=PROFILES[provider]
        data={'grant_type':'authorization_code','code':code,'redirect_uri':self.redirect(provider),'client_id':'fixture-'+provider,'client_secret':'fixture-only-secret'}
        if profile['pkce']:data['code_verifier']=self.service.secrets.get(principal.tenant_id,'connector:verifier:'+event['id'],principal)
        tokens=self.http.request('POST',profile['token'],data=data).json()
        self.validate_tokens(provider,row,tokens)
        method,url=profile['identity'];kwargs={'headers':{'Authorization':'Bearer '+tokens['access_token']}}
        if provider=='hubspot':kwargs={'data':{'client_id':'fixture-hubspot','client_secret':'fixture-only-secret','token_type_hint':'access_token','access_token':tokens['access_token']}}
        account=self.http.request(method,url,**kwargs).json()
        expected={'google':'fixture-owner@example.invalid','outlook':'fixture-account','calendly':'https://api.calendly.com/users/fixture-account','hubspot':123}[provider]
        actual=account.get('email') if provider=='google' else account.get('id') if provider=='outlook' else account.get('resource',{}).get('uri') if provider=='calendly' else account.get('hub_id')
        if actual!=expected or provider=='google' and account.get('email_verified') is not True or provider=='hubspot' and account.get('active') is not True:raise DomainError('oauth_account_mismatch',403)
        tokens['expires_at']=(self.clock()+timedelta(seconds=min(int(tokens['expires_in']),3600))).isoformat()
        with self.service.store.transaction():
            current=self.service.row(principal,identity)
            if current['revision']!=row['revision']:raise DomainError('conflict',409)
            self.service.secrets.put(principal.tenant_id,'connector:oauth:'+identity,json.dumps(tokens),principal)
            current=self.service.store.update('operations_events',principal.tenant_id,identity,{'state':'connected','revision':row['revision']+1,'failure_code':None,'oauth_verified':True})
        return self.service.project(current)
    @staticmethod
    def validate_tokens(provider,row,tokens):
        scopes=tokens.get('scopes',tokens.get('scope','').split())
        if not tokens.get('access_token') or not tokens.get('refresh_token') or not set(required_scopes(provider,row['actions']))<=set(scopes) or not isinstance(tokens.get('expires_in'),int) or tokens['expires_in']<=0:raise DomainError('oauth_denied',403)
    def token(self,principal,row):
        with self.lock:
            row=self.service.row(principal,row['id'])
            if row['state']!='connected' or not row.get('oauth_verified'):raise DomainError('unconfigured',503)
            tokens=json.loads(self.service.secrets.get(principal.tenant_id,'connector:oauth:'+row['id'],principal))
            if self.clock().isoformat()<tokens['expires_at']:return tokens['access_token']
            try:
                response=self.http.request('POST',PROFILES[row['provider']]['token'],data={'grant_type':'refresh_token','refresh_token':tokens['refresh_token'],'client_id':'fixture-'+row['provider'],'client_secret':'fixture-only-secret'})
                fresh=response.json();updated={**tokens,**fresh};self.validate_tokens(row['provider'],row,updated)
                updated['expires_at']=(self.clock()+timedelta(seconds=min(updated['expires_in'],3600))).isoformat()
            except DomainError:
                with self.service.store.transaction():
                    if self.service.row(principal,row['id'])==row:self.service.store.update('operations_events',principal.tenant_id,row['id'],{'state':'needs_reauthorization','revision':row['revision']+1,'failure_code':'oauth_expired'})
                raise
            with self.service.store.transaction():
                if self.service.row(principal,row['id'])!=row:raise DomainError('conflict',409)
                self.service.secrets.put(principal.tenant_id,'connector:oauth:'+row['id'],json.dumps(updated),principal)
            return updated['access_token']
