"""Provider-specific REST codecs behind an injected offline transport, never a URL executor."""
from datetime import datetime, timezone
from hashlib import sha256
from urllib.parse import quote
import hmac
import json
import httpx
from .domain import DomainError

GOOGLE='https://www.googleapis.com/auth/calendar.'
PROFILES={
    'google':{'authorize':'https://accounts.google.com/o/oauth2/v2/auth','token':'https://oauth2.googleapis.com/token',
              'base':'https://www.googleapis.com/calendar/v3/','pkce':True,'identity':('GET','https://openidconnect.googleapis.com/v1/userinfo'),
              'scopes':['openid','email',GOOGLE+'calendarlist.readonly']},
    'outlook':{'authorize':'https://login.microsoftonline.com/common/oauth2/v2.0/authorize','token':'https://login.microsoftonline.com/common/oauth2/v2.0/token',
               'base':'https://graph.microsoft.com/v1.0/','pkce':True,'identity':('GET','https://graph.microsoft.com/v1.0/me'),
               'scopes':['openid','offline_access','User.Read']},
    'calendly':{'authorize':'https://auth.calendly.com/oauth/authorize','token':'https://auth.calendly.com/oauth/token',
                'base':'https://api.calendly.com/','pkce':True,'identity':('GET','https://api.calendly.com/users/me'),
                'scopes':['users:read','event_types:read']},
    'hubspot':{'authorize':'https://app.hubspot.com/oauth/authorize','token':'https://api.hubspot.com/oauth/v3/token',
               'base':'https://api.hubspot.com/','pkce':False,'identity':('POST','https://api.hubspot.com/oauth/v3/token/introspect'),
               'scopes':['oauth']},
}
ACTION_SCOPES={
    'google':{'availability':[GOOGLE+'freebusy'],'create':[GOOGLE+'events.owned'],'reschedule':[GOOGLE+'events.owned'],'cancel':[GOOGLE+'events.owned']},
    'outlook':{'availability':['Calendars.ReadBasic'],'create':['Calendars.ReadWrite'],'reschedule':['Calendars.ReadWrite'],'cancel':['Calendars.ReadWrite']},
    'calendly':{'availability':['availability:read'],'scheduled_events':['scheduled_events:read']},
    'hubspot':{'contact_read':['crm.objects.contacts.read'],'contact_write':['crm.objects.contacts.read','crm.objects.contacts.write']},
}

def required_scopes(provider,actions):
    return sorted(set(PROFILES[provider]['scopes']).union(*(ACTION_SCOPES[provider][action] for action in actions)))

class OfflineProviderHTTP:
    def __init__(self,transport):
        if not isinstance(transport,httpx.MockTransport):raise DomainError('forbidden',403)
        self.transport=transport
    def request(self,method,url,**kwargs):
        try:
            with httpx.Client(transport=self.transport,timeout=10,follow_redirects=False) as client:
                response=client.request(method,url,**kwargs)
        except httpx.TimeoutException:raise DomainError('delivery_unknown' if method in ('POST','PATCH','DELETE') else 'provider_error',504) from None
        except httpx.HTTPError:raise DomainError('provider_error',502) from None
        if len(response.content)>1_000_000:raise DomainError('provider_error',502)
        if response.status_code==401:raise DomainError('google_not_connected',503)
        if response.status_code==403:raise DomainError('forbidden',403)
        if response.status_code==429:raise DomainError('provider_rate_limited',429)
        if response.status_code==412:raise DomainError('stale_event',409)
        if response.status_code>=500:raise DomainError('delivery_unknown' if method in ('POST','PATCH','DELETE') else 'provider_error',502)
        if response.status_code not in (200,201,204,404,409):raise DomainError('provider_error',502)
        if response.status_code != 204:
            try:
                if not isinstance(response.json(),dict):raise ValueError()
            except (ValueError,TypeError):
                raise DomainError('delivery_unknown' if method in ('POST','PATCH','DELETE') else 'provider_error',502) from None
        return response

class ProductionProviderHTTP(OfflineProviderHTTP):
    """Explicit server-side activation, fixed provider egress and bounded HTTP.

    No transport is opened until request(); construction requires the operator's
    reviewed activation flag. An injected MockTransport supports contract tests.
    """
    def __init__(self, providers, *, approved=False, transport=None):
        if approved is not True or not providers or set(providers)-set(PROFILES):
            raise DomainError('unconfigured',503)
        self.providers=set(providers)
        self.transport=transport

    def request(self,method,url,**kwargs):
        from urllib.parse import urlsplit,unquote
        parsed=urlsplit(url)
        if parsed.scheme!='https' or parsed.username or parsed.password or parsed.fragment or parsed.query or '..' in unquote(parsed.path).split('/') or parsed.port not in (None,443):
            raise DomainError('forbidden',403)
        if method not in ('GET','POST','PATCH','DELETE'):
            raise DomainError('forbidden',403)
        permitted=False
        for provider in self.providers:
            profile=PROFILES[provider]
            if url in (profile['token'],profile['identity'][1]) or url.startswith(profile['base']):
                permitted=True
        if not permitted:
            raise DomainError('forbidden',403)
        # Do not accept callers' alternate transport, timeout, redirect or TLS policy.
        if set(kwargs)-{'headers','params','data','json'}:
            raise DomainError('forbidden',403)
        return super().request(method,url,**kwargs)

class ProviderAdapter:
    def __init__(self,provider,http,*,synthetic_only=True):self.provider,self.http,self.synthetic_only=provider,http,synthetic_only
    def call(self,token,method,path,**kwargs):
        return self.http.request(method,PROFILES[self.provider]['base']+path,headers={'Authorization':'Bearer '+token,**kwargs.pop('headers',{})},**kwargs)
    def resources(self,token):
        path={'google':'users/me/calendarList','outlook':'me/calendars','calendly':'event_types','hubspot':'crm/v3/properties/contacts'}[self.provider]
        response=self.call(token,'GET',path)
        if response.status_code!=200:raise DomainError('provider_error',502)
        data=response.json();items=data.get({'google':'items','outlook':'value','calendly':'collection','hubspot':'results'}[self.provider],[])
        # Do not expose vendor response bodies, owner identities or arbitrary discovered fields.
        return [{'id':str(item.get('id') or item.get('uri') or item.get('name')),
                 'writable':item.get('accessRole')=='owner' if self.provider=='google' else item.get('canEdit',False) if self.provider=='outlook' else False}
                for item in items if item.get('id') or item.get('uri') or item.get('name')]
    def execute(self,token,action,resource,args,key,*,account_type='work',owned=False,consent=False):
        if action not in ACTION_SCOPES[self.provider]:raise DomainError('invalid_input',422)
        writing=action in ('create','reschedule','cancel','contact_write')
        if writing and (not consent or not owned):raise DomainError('forbidden',403)
        identity=quote(resource,safe='');event=quote(args.get('event_id',''),safe='')
        if action in ('reschedule','cancel') and not event:raise DomainError('invalid_input',422)
        if self.provider in ('google','outlook'):
            if action!='cancel':
                try:
                    start=datetime.fromisoformat(args['start']);end=datetime.fromisoformat(args['end'])
                    if start.tzinfo is None or end.tzinfo is None or end<=start:raise ValueError()
                except (ValueError,KeyError,TypeError):raise DomainError('invalid_input',422) from None
            if self.provider=='google':
                path='calendars/'+identity+'/events'
                body={'summary':'Synthetic demo','start':{'dateTime':args.get('start')},'end':{'dateTime':args.get('end')}}
                if action=='availability':method,path,body='POST','freeBusy',{'timeMin':args['start'],'timeMax':args['end'],'items':[{'id':resource}]}
                elif action=='create':method='POST';body['id']=sha256(key.encode()).hexdigest()
                elif action=='reschedule':method,path='PATCH',path+'/'+event
                else:method,path,body='DELETE',path+'/'+event,None
                extra={'params':{'sendUpdates':'none'}} if writing else {}
                if action in ('reschedule','cancel'):
                    if not args.get('etag'):raise DomainError('stale_event',409)
                    extra['headers']={'If-Match':args['etag']}
            else:
                path='me/calendars/'+identity+'/events'
                body={'subject':'Synthetic demo','start':{'dateTime':start.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),'timeZone':'UTC'},'end':{'dateTime':end.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S'),'timeZone':'UTC'}} if action!='cancel' else None
                if action=='availability':
                    if account_type!='work':raise DomainError('invalid_input',422)
                    method,path,body='POST','me/calendar/getSchedule',{'schedules':[resource],'startTime':body['start'],'endTime':body['end'],'availabilityViewInterval':30}
                elif action=='create':method='POST';body['transactionId']=key
                elif action=='reschedule':method,path='PATCH',path+'/'+event
                else:method,path='DELETE',path+'/'+event
                extra={}
                if action in ('reschedule','cancel'):
                    if not args.get('etag'):raise DomainError('stale_event',409)
                    extra['headers']={'If-Match':args['etag']}
            response=self.call(token,method,path,json=body,**extra)
        elif self.provider=='calendly':
            path='event_type_available_times' if action=='availability' else 'scheduled_events'
            params={'event_type':resource,'start_time':args.get('start'),'end_time':args.get('end')} if action=='availability' else {'user':resource}
            response=self.call(token,'GET',path,params=params)
        else:
            # Narrow CRM mapping: no lifecycle stages, arbitrary properties, or account-wide writes.
            properties=args.get('properties',{})
            if set(properties)-{'email','firstname','lastname','company'}:raise DomainError('invalid_input',422)
            if action=='contact_read':response=self.call(token,'GET','crm/v3/objects/contacts/'+identity)
            else:
                if not isinstance(properties.get('email'), str) or '@' not in properties['email'] or len(properties['email']) > 254 or '\n' in properties['email'] or '\r' in properties['email'] or self.synthetic_only and not properties['email'].endswith('@example.invalid'):raise DomainError('invalid_input',422)
                # Explicit unique email lookup avoids partial-upsert semantics and duplicate creates.
                existing=self.call(token,'GET','crm/v3/objects/contacts/'+quote(properties['email'],safe=''),params={'idProperty':'email'})
                if existing.status_code==200:
                    response=self.call(token,'PATCH','crm/v3/objects/contacts/'+quote(str(existing.json()['id']),safe=''),json={'properties':properties})
                elif existing.status_code==404:response=self.call(token,'POST','crm/v3/objects/contacts',json={'properties':properties})
                else:raise DomainError('conflict',409)
        if response.status_code in (404,409):raise DomainError('conflict',409)
        data=response.json() if response.content else {}
        result={'provider_id':str(data.get('id','')),'status':'SIMULATED' if self.synthetic_only else 'PROVIDER_ACCEPTED_UNVERIFIED'}
        if action=='availability':
            if self.provider=='google':
                calendar=data.get('calendars',{}).get(resource)
                if not calendar or calendar.get('errors') or 'busy' not in calendar:raise DomainError('provider_error',502)
                result['available']=not calendar['busy']
            elif self.provider=='outlook':
                schedules=data.get('value',[])
                if not schedules or any(item.get('error') or 'scheduleItems' not in item for item in schedules):raise DomainError('provider_error',502)
                result['available']=all(not any(event.get('status')!='free' for event in item['scheduleItems']) for item in schedules)
            else:result['available']=bool(data.get('collection'))
        return result

class ProductionProviderAdapter(ProviderAdapter):
    """Capability-limited real codecs, separate from synthetic-only fixture policy."""
    def __init__(self,provider,http):
        super().__init__(provider,http,synthetic_only=False)

    def resources(self,token,*,account_id=None):
        if self.provider=='google':
            response=self.call(token,'GET','users/me/calendarList')
            data=response.json()
            if response.status_code!=200 or data.get('nextPageToken'):
                raise DomainError('provider_error',502)
            return [{'id':item['id'],'writable':item.get('accessRole')=='owner','primary':item.get('primary') is True} for item in data.get('items',[]) if isinstance(item.get('id'),str)]
        if self.provider=='calendly':
            if not account_id or not account_id.startswith('https://api.calendly.com/users/'):
                raise DomainError('forbidden',403)
            response=self.call(token,'GET','event_types',params={'user':account_id})
            if response.status_code!=200 or response.json().get('pagination',{}).get('next_page_token'):
                raise DomainError('provider_error',502)
            return [{'id':item['uri'],'writable':False} for item in response.json().get('collection',[])
                    if isinstance(item.get('uri'),str) and item['uri'].startswith('https://api.calendly.com/event_types/')]
        if self.provider=='hubspot':
            if not account_id or not account_id.isdigit():
                raise DomainError('forbidden',403)
            response=self.call(token,'GET','crm/v3/properties/contacts')
            if response.status_code!=200:
                raise DomainError('provider_error',502)
            return [{'id':'hubspot:'+account_id,'writable':True}]
        return super().resources(token)

    def execute(self,token,action,resource,args,key,*,account_type='work',owned=False,consent=False):
        if self.provider=='outlook' and action=='availability':
            if account_type not in ('work','personal'):
                raise DomainError('forbidden',403)  # Shared-resource scopes are not assumed.
            try:
                start=datetime.fromisoformat(args['start']);end=datetime.fromisoformat(args['end'])
                if start.tzinfo is None or end.tzinfo is None or end<=start:
                    raise ValueError()
            except (TypeError,ValueError,KeyError):
                raise DomainError('invalid_input',422) from None
            response=self.call(token,'GET','me/calendars/'+quote(resource,safe='')+'/calendarView',
                params={'startDateTime':start.isoformat(),'endDateTime':end.isoformat(),'$select':'showAs,isAllDay,start,end','$top':1000},
                headers={'Prefer':'outlook.timezone="UTC"'})
            data=response.json()
            if response.status_code!=200 or not isinstance(data.get('value'),list) or data.get('@odata.nextLink'):
                raise DomainError('provider_error',502)  # Incomplete pagination cannot claim a free slot.
            return {'provider_id':'','status':'PROVIDER_ACCEPTED_UNVERIFIED',
                    'available':all(item.get('showAs')=='free' for item in data['value'])}
        if self.provider=='calendly' and action=='scheduled_events':
            # The verified account is a server-side binding, not an arbitrary
            # caller-provided URL. Public action registration remains gated.
            if not resource.startswith('https://api.calendly.com/users/'):
                raise DomainError('forbidden',403)
        return super().execute(token,action,resource,args,key,account_type=account_type,owned=owned,consent=consent)


def calendly_signature(raw,header,secret,at):
    try:
        parts=dict(item.split('=',1) for item in header.split(','));stamp=int(parts['t'])
        if abs(at.timestamp()-stamp)>180:raise ValueError()
        expected=hmac.new(secret.encode(),str(stamp).encode()+b'.'+raw,'sha256').hexdigest()
        if not hmac.compare_digest(expected,parts['v1']):raise ValueError()
    except (ValueError,KeyError):raise DomainError('unauthorized',401) from None
    return sha256(raw).hexdigest()
