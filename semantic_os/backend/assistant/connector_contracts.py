"""Reviewed production connector configuration contracts; no registration or network access."""
from typing import Literal
from urllib.parse import urlsplit
from pydantic import Field,field_validator,model_validator
from .domain import Contract
from .connector_adapters import ACTION_SCOPES,required_scopes

ConnectionState=Literal['disconnected','connecting','connected','degraded','reauthorization_required','revoked','unsupported']

class PlatformOAuthApplication(Contract):
    provider:Literal['google','outlook','calendly','hubspot']
    client_id:str=Field(min_length=1,max_length=300)
    secret_reference:str=Field(pattern=r'^platform:oauth:(google|outlook|calendly|hubspot):client_secret$')
    redirect_uri:str=Field(max_length=500)
    allowed_redirects:list[str]=Field(min_length=1,max_length=5)
    @model_validator(mode='after')
    def exact_redirect(self):
        parsed=urlsplit(self.redirect_uri)
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or self.redirect_uri not in self.allowed_redirects:raise ValueError('Exact HTTPS redirect required')
        if self.secret_reference!='platform:oauth:'+self.provider+':client_secret':raise ValueError('Provider credential mismatch')
        if parsed.path!='/backend/api/connectors/oauth/'+self.provider+'/callback':raise ValueError('Provider callback mismatch')
        return self

class CustomerConnectionConfig(Contract):
    provider:Literal['google','outlook','calendly','hubspot']
    actions:list[str]=Field(min_length=1,max_length=8)
    resource_ids:list[str]=Field(default_factory=list,max_length=8)
    revision:int=Field(ge=1)
    @model_validator(mode='after')
    def supported(self):
        if len(set(self.actions))!=len(self.actions) or set(self.actions)-set(ACTION_SCOPES[self.provider]):raise ValueError('Unsupported capability')
        if len(set(self.resource_ids))!=len(self.resource_ids):raise ValueError('Duplicate resource')
        if any(not value or len(value)>250 or '\n' in value for value in self.resource_ids):raise ValueError('Invalid resource')
        return self
    def consent_scopes(self):return required_scopes(self.provider,self.actions)

class RedactedConnection(Contract):
    contract_version:Literal[1]=1
    id:str
    provider:Literal['google','outlook','calendly','hubspot']
    state:ConnectionState
    revision:int=Field(ge=1)
    actions:list[str]
    verification:Literal['NOT_TESTED','OFFLINE_PASS','LIVE_VERIFIED','BLOCKED']
    failure_code:str|None=None
    @model_validator(mode='after')
    def verified_connection(self):
        if self.state=='connected' and self.verification!='LIVE_VERIFIED':raise ValueError('Fixture is not a live connection')
        return self
