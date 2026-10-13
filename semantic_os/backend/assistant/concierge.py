"""Concierge policy and durable external actions, delegated to the existing executor."""
import base64
from datetime import date,datetime,timedelta,time,timezone
from email.message import EmailMessage
from hashlib import sha256
import hmac
import io
import json
import secrets
from threading import RLock
from typing import Literal
from urllib.parse import quote
from zoneinfo import ZoneInfo
from pydantic import Field,StrictBool,field_validator,model_validator
from .domain import Contract,DomainError,Locale
from .messaging_adapters import mailbox
from .store import uid
from .language import format_date
from .saas_domain import UsageEvent,UNITS

TOOLS=('ConciergeAvailability','ConciergeBooking','ConciergeManage','ConciergeRequest')

class ConciergePolicy(Contract):
    enabled:bool=False
    calendar_id:str=Field(default='primary',max_length=250)
    busy_calendars:list[str]=Field(default_factory=list,max_length=5)
    timezone:Literal['Europe/Sofia']='Europe/Sofia'
    weekdays:list[int]=Field(default_factory=lambda:[0,1,2,3,4])
    opens:Literal['10:00']='10:00'
    closes:Literal['19:00']='19:00'
    duration_minutes:int=Field(default=30,ge=15,le=120)
    buffer_minutes:int=Field(default=15,ge=0,le=60)
    slot_minutes:int=Field(default=15,ge=5,le=60)
    ends_on:date=date(2026,12,31)
    reminder_time:time=time(8)
    fallback_minutes:int=Field(default=60,ge=5,le=120)
    business_inbox:str=Field(default='mariya.manolova92@gmail.com',max_length=250)
    management_origin:str=Field(default='',max_length=300)
    operations_authorized:StrictBool=False
    meet_authorized:StrictBool=False
    request_retention_days:int=Field(default=30,ge=1,le=365)
    @field_validator('weekdays')
    @classmethod
    def days(cls,value):
        if not value or len(set(value))!=len(value) or any(type(day)!=int or day not in range(5) for day in value):raise ValueError('Mon-Fri only')
        return value
    @field_validator('business_inbox')
    @classmethod
    def inbox(cls,value):return mailbox(value)

class ConciergeAvailability(Contract):
    day:date
    booking_id:str|None=None
    management_token:str|None=Field(default=None,max_length=2000)

class ConciergeBooking(Contract):
    starts_at:datetime
    name:str=Field(min_length=1,max_length=120)
    email:str=Field(max_length=250)
    topic:str=Field(min_length=1,max_length=1000)
    company:str=Field(default='',max_length=120)
    verification_id:str=Field(max_length=100)
    consent:Literal[True]
    @field_validator('name','topic')
    @classmethod
    def meaningful(cls,value):
        if not value.strip():raise ValueError('required value')
        return value.strip()
    @field_validator('email')
    @classmethod
    def address(cls,value):return mailbox(value)

class ConciergeManage(Contract):
    action:Literal['reschedule','cancel']
    management_token:str=Field(max_length=2000)
    starts_at:datetime|None=None
    consent:Literal[True]

class ConciergeRequest(Contract):
    action:Literal['information','business','feature']
    name:str=Field(default='',max_length=120)
    email:str=Field(default='',max_length=250)
    company:str=Field(default='',max_length=150)
    topic:str=Field(min_length=1,max_length=1500)
    timeline:str=Field(default='',max_length=200)
    impact:str=Field(default='',max_length=1000)
    verification_id:str=Field(default='',max_length=100)
    consent:Literal[True]
    marketing_consent:StrictBool=False
    @model_validator(mode='after')
    def required_details(self):
        if not self.topic.strip():raise ValueError('topic required')
        if self.action!='feature' and (not self.name.strip() or not self.email.strip()):raise ValueError('name and email required')
        if self.action=='business' and not self.company.strip():raise ValueError('company required')
        if self.action=='feature' and not self.impact.strip():raise ValueError('use case and impact required')
        return self

SCHEMAS=dict(zip(TOOLS,(ConciergeAvailability,ConciergeBooking,ConciergeManage,ConciergeRequest)))

class Concierge:
    def __init__(self,store,engine,google,secret_store,*,public_origin=''):
        self.store,self.engine,self.google,self.secrets=store,engine,google,secret_store
        self.clock=engine.clock;self.public_origin=public_origin;self.locks={};self.guard=RLock()
        self.widget=None
        from .tools import SCHEMAS as registry
        registry.update(SCHEMAS)
        engine.tools.extensions={name:self for name in TOOLS}

    def rows(self,tenant,kind):return [row for row in self.store.list('operations_events',tenant) if row.get('kind')==kind]
    def policy(self,tenant):
        row=self.store.find('operations_events',tenant,'concierge:policy')
        if not row:raise DomainError('concierge_unavailable',503)
        return ConciergePolicy.model_validate(row['policy'])

    def configure(self,principal,policy):
        principal.require('configure')
        from .widget import origin
        if policy.management_origin:policy.management_origin=origin(policy.management_origin,local=self.google.development)
        if policy.management_origin and policy.management_origin!=self.public_origin:raise DomainError('invalid_input',422)
        if policy.request_retention_days>self.store.tenant(principal.tenant_id)['retention_days']:raise DomainError('invalid_input',422)
        if policy.enabled and not policy.management_origin:raise DomainError('invalid_input',422)
        with self.store.transaction():
            row=self.store.find('operations_events',principal.tenant_id,'concierge:policy')
            data={'kind':'concierge_policy','policy':policy.model_dump(mode='json')}
            if row:self.store.update('operations_events',principal.tenant_id,row['id'],data)
            else:
                self.store.add('operations_events',principal.tenant_id,data,external_key='concierge:policy')
                self.secrets.put(principal.tenant_id,'concierge:signing',secrets.token_hex(32),principal)
            self.store.audit(principal,'concierge:policy_changed')
            if policy.enabled:
                agent=self.store.get('agents',principal.tenant_id,'executor')
                self.store.update('agents',principal.tenant_id,agent['id'],{'allowed_tools':list(dict.fromkeys([*agent['allowed_tools'],*TOOLS]))})
        return policy.model_dump(mode='json')

    def ready(self,tenant,write=False):
        policy=self.policy(tenant)
        if not policy.enabled:raise DomainError('concierge_unavailable',503)
        kinds=('calendar','gmail') if write else ('calendar',)
        if any(not (row:=self.google.row(tenant,kind)) or row['state']!='connected' for kind in kinds):raise DomainError('google_not_connected',503)
        if write and not policy.operations_authorized:raise DomainError('live_operations_not_authorized',403)
        return policy

    def bounds(self,policy,day):
        zone=ZoneInfo(policy.timezone)
        if day.weekday() not in policy.weekdays or day>policy.ends_on or day<self.clock().astimezone(zone).date():raise DomainError('outside_booking_window',422)
        return datetime.combine(day,time(10),zone),datetime.combine(day,time(19),zone)

    def valid_start(self,policy,value):
        if value.tzinfo is None:raise DomainError('timezone_required',422)
        start=value.astimezone(ZoneInfo(policy.timezone));low,high=self.bounds(policy,start.date())
        end=start+timedelta(minutes=policy.duration_minutes)
        if start<=self.clock() or start<low or end>high or start.second or start.microsecond or start.minute%policy.slot_minutes:raise DomainError('outside_booking_window',422)
        return start,end

    def busy(self,tenant,policy,day,exclude=None):
        low,high=self.bounds(policy,day);buffer=timedelta(minutes=policy.buffer_minutes)
        calendars=list(dict.fromkeys([policy.calendar_id,*policy.busy_calendars]))
        owned_busy=[]
        if exclude:
            if exclude['calendar_id']!=policy.calendar_id:raise DomainError('stale_event',409)
            owned=self.google.call(tenant,'calendar','GET','calendars/'+quote(policy.calendar_id,safe='')+'/events/'+exclude['event_id'])
            if owned.status_code!=200 or owned.json().get('status')!='confirmed' or owned.json().get('extendedProperties',{}).get('private',{}).get('concierge_booking')!=exclude['id']:raise DomainError('stale_event',409)
            # For a proven owned event, list only minimal event fields so we can
            # exclude that exact ID without subtracting merged FreeBusy periods.
            path='calendars/'+quote(policy.calendar_id,safe='')+'/events';page=None
            for _ in range(5):
                params={'timeMin':(low-buffer).isoformat(),'timeMax':(high+buffer).isoformat(),'singleEvents':'true','maxResults':2500,'fields':'items(id,status,transparency,start,end),nextPageToken'}
                if page:params['pageToken']=page
                response=self.google.call(tenant,'calendar','GET',path,params=params)
                if response.status_code!=200:raise DomainError('availability_unavailable',503)
                for item in response.json().get('items',[]):
                    if item['id']==exclude['event_id'] or item.get('status')=='cancelled' or item.get('transparency')=='transparent':continue
                    def value(part):
                        if part.get('dateTime'):
                            result=datetime.fromisoformat(part['dateTime'].replace('Z','+00:00'))
                            if result.tzinfo is None:raise DomainError('provider_error',502)
                            return result
                        return datetime.combine(date.fromisoformat(part['date']),time(),ZoneInfo(policy.timezone))
                    owned_busy.append((value(item['start'])-buffer,value(item['end'])+buffer))
                page=response.json().get('nextPageToken')
                if not page:break
            if page:raise DomainError('availability_unavailable',503)
            calendars=[item for item in calendars if item!=policy.calendar_id]
            if not calendars:return owned_busy
        response=self.google.call(tenant,'calendar','POST','freeBusy',json={'timeMin':(low-buffer).isoformat(),'timeMax':(high+buffer).isoformat(),'timeZone':policy.timezone,'items':[{'id':value} for value in calendars]})
        if response.status_code!=200:raise DomainError('availability_unavailable',503)
        values=response.json().get('calendars',{});busy=owned_busy
        for identifier in calendars:
            item=values.get(identifier) or (values.get(self.google.row(tenant,'calendar')['account']) if identifier=='primary' else None)
            if item is None or item.get('errors'):raise DomainError('availability_unavailable',503)
            for period in item.get('busy',[]):
                start=datetime.fromisoformat(period['start'].replace('Z','+00:00'));end=datetime.fromisoformat(period['end'].replace('Z','+00:00'))
                if start.tzinfo is None or end.tzinfo is None or end<=start:raise DomainError('provider_error',502)
                busy.append((start-buffer,end+buffer))
        # FreeBusy cannot identify an event. Never subtract an assumed matching
        # period: overlapping private events could share its boundaries.
        return busy

    def slots(self,tenant,day,exclude=None):
        policy=self.ready(tenant);low,high=self.bounds(policy,day);busy=self.busy(tenant,policy,day,exclude=exclude);slots=[]
        current=low
        while current+timedelta(minutes=policy.duration_minutes)<=high:
            end=current+timedelta(minutes=policy.duration_minutes)
            if current>self.clock() and not any(current<b and end>a for a,b in busy):slots.append(current.isoformat())
            current+=timedelta(minutes=policy.slot_minutes)
        return {'slots':slots,'timezone':policy.timezone,'duration_minutes':policy.duration_minutes,'state':'LIVE'}

    def queue_email(self,tenant,conversation,recipient,subject,body,key,*,booking_id=None,due=None):
        with self.store.transaction():
            previous=self.store.find('jobs',tenant,'concierge-mail:'+key)
            if previous:return previous
            job=self.store.add('jobs',tenant,{'kind':'concierge_email','conversation_id':conversation,'recipient':mailbox(recipient),'subject':subject,'status':'pending','attempts':0,'due_at':(due or self.clock()).isoformat(),'booking_id':booking_id},external_key='concierge-mail:'+key)
            self.secrets.put(tenant,'concierge:mail:'+job['id'],body)
            return job

    def verify_email(self,actor,conversation,email):
        policy=self.policy(actor.tenant_id)
        if not policy.enabled or not policy.operations_authorized:raise DomainError('live_operations_not_authorized',403)
        row=self.google.row(actor.tenant_id,'gmail')
        if not row or row['state']!='connected':raise DomainError('google_not_connected',503)
        email=mailbox(email)
        # At most three verification deliveries per scoped conversation.
        if sum(row.get('conversation_id')==conversation['id'] for row in self.rows(actor.tenant_id,'concierge_email_verification'))>=3:raise DomainError('limit_reached',429)
        code=str(secrets.randbelow(1000000)).zfill(6);identity=uid();key=self.secrets.get(actor.tenant_id,'concierge:signing')
        row=self.store.add('operations_events',actor.tenant_id,{'kind':'concierge_email_verification','conversation_id':conversation['id'],'email':email,'status':'pending','attempts':0,
            'code_hash':hmac.new(key.encode(),(identity+code).encode(),sha256).hexdigest(),'expires_at':(self.clock()+timedelta(minutes=10)).isoformat()},id=identity)
        bg=conversation.get('active_locale')=='bg-BG'
        job=self.queue_email(actor.tenant_id,conversation['id'],email,'Потвърдете имейла си' if bg else 'Verify your email',('Код за потвърждение: ' if bg else 'Your verification code: ')+code,'verify:'+identity)
        self.store.update('jobs',actor.tenant_id,job['id'],{'verification_id':identity})
        return {'verification_id':identity,'status':'queued','expires_in':600}

    def confirm_email(self,actor,conversation,identity,code):
        with self.store.transaction():
            row=self.store.get('operations_events',actor.tenant_id,identity)
            if row.get('kind')!='concierge_email_verification' or row['conversation_id']!=conversation['id'] or row['status'] not in ('pending','verified') or row['attempts']>=5 or datetime.fromisoformat(row['expires_at'])<=self.clock():raise DomainError('verification_required',403)
            key=self.secrets.get(actor.tenant_id,'concierge:signing')
            accepted=hmac.compare_digest(row['code_hash'],hmac.new(key.encode(),(identity+code).encode(),sha256).hexdigest())
            if row['status']=='verified':
                if accepted:return {'verified':True}
                raise DomainError('verification_required',403)
            self.store.update('operations_events',actor.tenant_id,identity,{'attempts':row['attempts']+1,'status':'verified' if accepted else 'pending'})
        if not accepted:raise DomainError('verification_required',403)
        return {'verified':True}

    def verified(self,tenant,conversation,identity,email):
        row=self.store.get('operations_events',tenant,identity)
        if row.get('kind')!='concierge_email_verification' or row['conversation_id']!=conversation or row['email']!=mailbox(email) or row['status']!='verified' or datetime.fromisoformat(row['expires_at'])<=self.clock():raise DomainError('verification_required',403)

    def management_token(self,tenant,booking):
        claim={'tenant':tenant,'booking':booking['id'],'revision':booking['revision'],'nonce':booking['management_nonce'],'expires':int((self.clock()+timedelta(days=7)).timestamp())}
        payload=base64.urlsafe_b64encode(json.dumps(claim,separators=(',',':')).encode()).decode().rstrip('=')
        key=self.secrets.get(tenant,'concierge:signing').encode();return payload+'.'+hmac.new(key,payload.encode(),sha256).hexdigest()

    def owned(self,tenant,token,*,stale=False):
        try:
            payload,signature=token.split('.');claim=json.loads(base64.urlsafe_b64decode(payload+'='*(-len(payload)%4)))
            if claim['tenant']!=tenant:raise ValueError()
            key=self.secrets.get(tenant,'concierge:signing').encode()
            if not hmac.compare_digest(signature,hmac.new(key,payload.encode(),sha256).hexdigest()) or claim['expires']<=self.clock().timestamp():raise ValueError()
            row=self.store.get('operations_events',tenant,claim['booking'])
            if row.get('kind')!='concierge_booking':raise ValueError()
            if not stale and (row['revision']!=claim['revision'] or row['management_nonce']!=claim['nonce']):raise ValueError()
            return row
        except (ValueError,KeyError,TypeError,DomainError):raise DomainError('ownership_required',403) from None

    def calendar_owner(self,tenant,policy):
        response=self.google.call(tenant,'calendar','GET','users/me/calendarList/'+quote(policy.calendar_id,safe=''))
        if response.status_code!=200 or response.json().get('accessRole')!='owner':raise DomainError('calendar_not_owned',403)
        return response.json()

    def schedule(self,tenant,booking):
        policy=self.policy(tenant);start=datetime.fromisoformat(booking['starts_at']);zone=ZoneInfo(policy.timezone)
        due=datetime.combine(start.astimezone(zone).date(),policy.reminder_time,zone)
        if due<=self.clock():due=start-timedelta(minutes=policy.fallback_minutes)
        if self.clock()<due<start:
            bg=booking['locale']=='bg-BG';self.queue_email(tenant,booking['conversation_id'],booking['email'],'Напомняне за демонстрация' if bg else 'Demo reminder',('Вашата демонстрация е на ' if bg else 'Your demo is at ')+format_date(start,booking['locale'],policy.timezone),'reminder:'+booking['id']+':'+str(booking['revision']),booking_id=booking['id'],due=due)

    def notify_management(self,tenant,booking):
        policy=self.policy(tenant);link=policy.management_origin+'/widget/manage/'+booking['public_id']+'#token='+self.management_token(tenant,booking)
        bg=booking['locale']=='bg-BG'
        self.queue_email(tenant,booking['conversation_id'],booking['email'],'Управление на демонстрацията' if bg else 'Manage your demo',('Номер на записването: ' if bg else 'Booking reference: ')+booking['id']+'\n'+('Промяна или отказ на Вашата демонстрация: ' if bg else 'Reschedule or cancel your demo: ')+link,'manage:'+booking['id']+':'+str(booking['revision']),booking_id=booking['id'])

    def recover_management(self,principal,conversation,booking_id,email,verification_id):
        self.ready(principal.tenant_id,True)
        self.verified(principal.tenant_id,conversation['id'],verification_id,email)
        booking=self.store.get('operations_events',principal.tenant_id,booking_id)
        if booking.get('kind')!='concierge_booking' or booking['status']!='confirmed' or booking['email']!=mailbox(email) or booking['public_id']!=conversation['widget_public_id']:raise DomainError('ownership_required',403)
        # Same revision, new email delivery; no management capability returned publicly.
        policy=self.policy(principal.tenant_id)
        link=policy.management_origin+'/widget/manage/'+booking['public_id']+'#token='+self.management_token(principal.tenant_id,booking)
        bg=conversation['active_locale']=='bg-BG'
        self.queue_email(principal.tenant_id,conversation['id'],booking['email'],'Нова връзка за управление' if bg else 'New management link',link,'recover:'+verification_id,booking_id=booking['id'])
        return {'status':'queued'}

    @staticmethod
    def event_times_match(event,start,end):
        try:
            actual_start=datetime.fromisoformat(event['start']['dateTime'].replace('Z','+00:00'))
            actual_end=datetime.fromisoformat(event['end']['dateTime'].replace('Z','+00:00'))
            return actual_start.tzinfo is not None and actual_end.tzinfo is not None and actual_start==start and actual_end==end
        except (KeyError,TypeError,ValueError,AttributeError):return False

    def create(self,principal,conversation,args,identity):
        tenant=principal.tenant_id;policy=self.ready(tenant,True);start,end=self.valid_start(policy,datetime.fromisoformat(args['starts_at']))
        self.verified(tenant,conversation['id'],args['verification_id'],args['email']);metadata=self.calendar_owner(tenant,policy)
        busy=self.busy(tenant,policy,start.date())
        if any(start<b and end>a for a,b in busy):raise DomainError('slot_unavailable',409)
        event_id=sha256(('concierge:'+tenant+identity).encode()).hexdigest()
        event={'id':event_id,'summary':'Демонстрация на Ontelyx' if conversation['active_locale']=='bg-BG' else 'Ontelyx demo','description':args['topic'],'start':{'dateTime':start.isoformat(),'timeZone':policy.timezone},'end':{'dateTime':end.isoformat(),'timeZone':policy.timezone},'attendees':[{'email':args['email'],'displayName':args['name']}],
            'extendedProperties':{'private':{'concierge_booking':identity}},'reminders':{'useDefault':False}}
        if policy.meet_authorized:
            if 'hangoutsMeet' not in metadata.get('conferenceProperties',{}).get('allowedConferenceSolutionTypes',[]):raise DomainError('meet_unavailable',409)
            event['conferenceData']={'createRequest':{'requestId':event_id,'conferenceSolutionKey':{'type':'hangoutsMeet'}}}
        path='calendars/'+quote(policy.calendar_id,safe='')+'/events'
        try:response=self.google.call(tenant,'calendar','POST',path,params={'sendUpdates':'all','conferenceDataVersion':1 if policy.meet_authorized else 0},json=event)
        except DomainError as error:
            if error.code!='delivery_unknown':raise
            response=self.google.call(tenant,'calendar','GET',path+'/'+event_id)
        if response.status_code==409:response=self.google.call(tenant,'calendar','GET',path+'/'+event_id)
        if response.status_code not in (200,201):raise DomainError('delivery_unknown',503)
        actual=response.json()
        if actual.get('id')!=event_id or actual.get('extendedProperties',{}).get('private',{}).get('concierge_booking')!=identity or actual.get('status')!='confirmed':raise DomainError('provider_error',502)
        if not self.event_times_match(actual,start,end):raise DomainError('delivery_unknown',503)
        return {'kind':'concierge_booking','conversation_id':conversation['id'],'assistant_ref':conversation['assistant_id'],'public_id':conversation['widget_public_id'],'event_id':event_id,'calendar_id':policy.calendar_id,
            'starts_at':start.isoformat(),'ends_at':end.isoformat(),'name':args['name'],'email':args['email'],'topic':args['topic'],'company':args.get('company',''),'locale':conversation['active_locale'],'status':'confirmed','etag':actual.get('etag'),
            'revision':1,'management_nonce':secrets.token_hex(16),'meet_url':actual.get('hangoutLink')}

    def manage(self,principal,conversation,args):
        tenant=principal.tenant_id;policy=self.ready(tenant,True);booking=self.owned(tenant,args['management_token'])
        if booking['assistant_ref']!=conversation['assistant_id'] or booking['public_id']!=conversation['widget_public_id'] or booking['status']!='confirmed':raise DomainError('ownership_required',403)
        path='calendars/'+quote(booking['calendar_id'],safe='')+'/events/'+booking['event_id']
        current=self.google.call(tenant,'calendar','GET',path)
        if current.status_code!=200 or current.json().get('extendedProperties',{}).get('private',{}).get('concierge_booking')!=booking['id'] or current.json().get('status')!='confirmed':raise DomainError('stale_event',409)
        etag=current.json().get('etag')
        if not etag:raise DomainError('stale_event',409)
        try:
            if datetime.fromisoformat(current.json()['start']['dateTime'])!=datetime.fromisoformat(booking['starts_at']) or datetime.fromisoformat(current.json()['end']['dateTime'])!=datetime.fromisoformat(booking['ends_at']):raise DomainError('stale_event',409)
        except (KeyError,ValueError):raise DomainError('stale_event',409) from None
        if args['action']=='cancel':
            response=self.google.call(tenant,'calendar','DELETE',path,headers={'If-Match':etag},params={'sendUpdates':'all'})
            if response.status_code!=204:raise DomainError('delivery_unknown',503)
            changes={'status':'cancelled','revision':booking['revision']+1,'management_nonce':secrets.token_hex(16)}
        else:
            if not args.get('starts_at'):raise DomainError('invalid_input',422)
            start,end=self.valid_start(policy,datetime.fromisoformat(args['starts_at']))
            if any(start<b and end>a for a,b in self.busy(tenant,policy,start.date(),exclude=booking)):raise DomainError('slot_unavailable',409)
            response=self.google.call(tenant,'calendar','PATCH',path,headers={'If-Match':etag},params={'sendUpdates':'all'},json={'start':{'dateTime':start.isoformat(),'timeZone':policy.timezone},'end':{'dateTime':end.isoformat(),'timeZone':policy.timezone}})
            if response.status_code!=200 or response.json().get('status')!='confirmed':raise DomainError('delivery_unknown',503)
            actual=response.json()
            if actual.get('id')!=booking['event_id'] or actual.get('extendedProperties',{}).get('private',{}).get('concierge_booking')!=booking['id'] or not self.event_times_match(actual,start,end):raise DomainError('delivery_unknown',503)
            changes={'starts_at':start.isoformat(),'ends_at':end.isoformat(),'etag':response.json().get('etag'),'revision':booking['revision']+1,'management_nonce':secrets.token_hex(16)}
        with self.store.transaction():
            changes['locale']=conversation['active_locale']
            self.store.update('operations_events',tenant,booking['id'],changes)
            appointment=self.store.find('appointments',tenant,'concierge:'+booking['id'])
            if appointment:self.store.update('appointments',tenant,appointment['id'],{key:changes[key] for key in ('starts_at','status') if key in changes})
            for job in self.store.list('jobs',tenant):
                if job.get('kind')=='concierge_email' and job.get('booking_id')==booking['id'] and job['status']=='pending':self.store.update('jobs',tenant,job['id'],{'status':'cancelled'})
        updated={**booking,**changes}
        if updated['status']=='confirmed':self.schedule(tenant,updated);self.notify_management(tenant,updated)
        return {'booking_id':booking['id'],'status':updated['status'],'starts_at':updated['starts_at'],'state':'LIVE'}

    def request(self,principal,conversation,args,identity):
        tenant=principal.tenant_id;policy=self.policy(tenant)
        if not policy.enabled:raise DomainError('concierge_unavailable',503)
        if args['email'] and args['action']=='information':self.verified(tenant,conversation['id'],args['verification_id'],args['email'])
        elif args['email']:args['email']=mailbox(args['email'])
        elif args['action']!='feature':raise DomainError('verification_required',403)
        row=self.store.find('operations_events',tenant,'concierge-request:'+identity)
        if not row:row=self.store.add('operations_events',tenant,{'kind':'concierge_request','conversation_id':conversation['id'],**args,'locale':conversation['active_locale'],'status':'received','notification_key':identity,'expires_at':(self.clock()+timedelta(days=policy.request_retention_days)).isoformat()},external_key='concierge-request:'+identity)
        if args['action']=='information':
            # Public links only, no arbitrary attachment or visitor-supplied HTML.
            bg=conversation['active_locale']=='bg-BG';body=('Информация за Ontelyx: ' if bg else 'Ontelyx product information: ')+'https://www.ontelyx.tech/platform\nhttps://www.ontelyx.tech/contact'
            self.queue_email(tenant,conversation['id'],args['email'],'Информация за Ontelyx' if bg else 'Ontelyx information',body,'information:'+identity)
        else:
            bg=conversation['active_locale']=='bg-BG'
            labels=('Име','Имейл','Компания','Тема и нужди','Срок','Влияние') if bg else ('Name','Email','Company','Topic and needs','Timeline','Impact')
            body='\n'.join(label+': '+args[key] for label,key in zip(labels,('name','email','company','topic','timeline','impact')))
            self.queue_email(tenant,conversation['id'],policy.business_inbox,('Запитване към Ontelyx' if bg else 'Ontelyx inquiry'),body,'inquiry:'+identity)
        return {'request_id':row['id'],'status':'received','notification':'queued'}

    def execute(self,principal,assistant,conversation,name,args,*,key,correlation_id,approved):
        if name!='ConciergeAvailability' and not approved:raise DomainError('forbidden',403)
        cachekey='concierge-action:'+conversation['id']+':'+key;fingerprint=sha256(json.dumps({'name':name,'args':args},sort_keys=True).encode()).hexdigest()
        # One connected owner account: serialize its calendars across tenants too.
        lockkey='google:mariya.manolova92@gmail.com'
        with self.guard:lock=self.locks.setdefault(lockkey,RLock())
        with lock:
            previous=self.store.find('operations_events',principal.tenant_id,cachekey)
            if previous:
                if previous['fingerprint']!=fingerprint:raise DomainError('conflict',409)
                if previous['status']=='completed':return previous['outcome']
                if previous['status']=='failed':raise DomainError(previous['error_code'],409)
                # Ambiguous remote writes must be reconciled, never automatically repeated.
                raise DomainError('delivery_unknown',409)
            if self.store.entitlements:
                for category in ('tool_executions','agent_executions'):
                    self.store.entitlements.record(principal.tenant_id,UsageEvent(resource_id=conversation['id'],category=category,quantity=1,unit=UNITS[category],provider='google',timestamp=self.clock(),correlation_id=correlation_id,idempotency_key=cachekey+':'+category))
            intent=self.store.add('operations_events',principal.tenant_id,{'kind':'concierge_intent','conversation_id':conversation['id'],'fingerprint':fingerprint,'tool':name,'status':'pending'},external_key=cachekey)
            try:
                if name=='ConciergeAvailability':data=self.slots(principal.tenant_id,date.fromisoformat(args['day']))
                elif name=='ConciergeBooking':
                    booking=self.create(principal,conversation,args,intent['id']+'-booking')
                    with self.store.transaction():
                        self.store.add('operations_events',principal.tenant_id,booking,id=intent['id']+'-booking')
                        # Google owns the stable identity; local booking ID is the intent ID.
                        row=self.store.get('operations_events',principal.tenant_id,intent['id']+'-booking')
                        self.store.add('appointments',principal.tenant_id,{'conversation_id':conversation['id'],'assistant_id':assistant['id'],'starts_at':booking['starts_at'],'duration_minutes':self.policy(principal.tenant_id).duration_minutes,'status':'confirmed','timezone':'Europe/Sofia','contact_name':booking['name'],'contact_email':booking['email'],'provider':'google','google_event_id':booking['event_id'],'concierge_booking_id':row['id']},external_key='concierge:'+row['id'])
                    self.schedule(principal.tenant_id,row);self.notify_management(principal.tenant_id,row)
                    data={'booking_id':row['id'],'status':'confirmed','starts_at':row['starts_at'],'meet_url':row['meet_url'],'state':'LIVE'}
                elif name=='ConciergeManage':data=self.manage(principal,conversation,args)
                else:data=self.request(principal,conversation,args,intent['id'])
                outcome={'status':'completed','code':'completed','data':data}
                with self.store.transaction():
                    self.store.update('operations_events',principal.tenant_id,intent['id'],{'status':'completed','outcome':outcome})
                    self.store.add('tool_executions',principal.tenant_id,{'conversation_id':conversation['id'],'agent':'executor','tool':name,'arguments':{k:v for k,v in args.items() if k not in ('management_token','verification_id')},'outcome':outcome,'correlation_id':correlation_id,'timestamp':self.clock().isoformat()},external_key=cachekey)
                    self.store.audit(principal,'tool:'+name,correlation_id=correlation_id,resource_id=intent['id'])
                return outcome
            except DomainError as error:
                self.store.update('operations_events',principal.tenant_id,intent['id'],{'status':'unknown' if error.code=='delivery_unknown' else 'failed','error_code':error.code})
                raise

    def worker(self):
        self.purge_requests()
        with self.store.lock:
            values=self.store.db.execute("SELECT data FROM jobs WHERE json_extract(data,'$.kind')='concierge_email' AND json_extract(data,'$.status')='pending' AND julianday(json_extract(data,'$.due_at'))<=julianday(?) ORDER BY julianday(json_extract(data,'$.due_at')) LIMIT 2",(self.clock().isoformat(),)).fetchall()
        for value in values:
            job=json.loads(value['data']);tenant=job['tenant_id']
            with self.guard:lock=self.locks.setdefault('google:mariya.manolova92@gmail.com',RLock())
            with lock:self.deliver(job)
        return len(values)

    def purge_requests(self):
        with self.store.lock:
            rows=self.store.db.execute("SELECT data FROM operations_events WHERE json_extract(data,'$.kind')='concierge_request' AND json_extract(data,'$.expires_at')<=? AND COALESCE(json_extract(data,'$.redacted'),0)=0 LIMIT 100",(self.clock().isoformat(),)).fetchall()
        for item in rows:
            row=json.loads(item['data']);tenant=row['tenant_id']
            self.store.update('operations_events',tenant,row['id'],{**{key:'' for key in ('name','email','company','topic','timeline','impact','verification_id')},'redacted':True})
            for record in self.store.list('tool_executions',tenant,row['conversation_id']):
                if record.get('outcome',{}).get('data',{}).get('request_id')==row['id']:
                    self.store.update('tool_executions',tenant,record['id'],{'arguments':{'redacted':True}})
                    for agent in self.store.list('agent_executions',tenant,row['conversation_id']):
                        if agent.get('handoff',{}).get('correlation_id')==record.get('correlation_id'):self.store.update('agent_executions',tenant,agent['id'],{'handoff':{**agent['handoff'],'arguments':{'redacted':True}}})
            for prefix in ('inquiry','information'):
                job=self.store.find('jobs',tenant,'concierge-mail:'+prefix+':'+row.get('notification_key',''))
                if job and job['status'] not in ('sending','delivery_unknown'):
                    self.store.update('jobs',tenant,job['id'],{'status':'cancelled','recipient':''})
                    self.secrets.put(tenant,'concierge:mail:'+job['id'],'')
        return len(rows)

    def deliver(self,job):
        tenant=job['tenant_id']
        try:
            policy=self.policy(tenant)
            if not policy.enabled or not policy.operations_authorized:return
            if job.get('verification_id'):
                verification=self.store.get('operations_events',tenant,job['verification_id'])
                if verification['status']!='pending' or datetime.fromisoformat(verification['expires_at'])<=self.clock():
                    self.store.update('jobs',tenant,job['id'],{'status':'cancelled'});return
            if job.get('booking_id'):
                booking=self.store.get('operations_events',tenant,job['booking_id'])
                if booking['status']!='confirmed' or datetime.fromisoformat(booking['starts_at'])<=self.clock():
                    self.store.update('jobs',tenant,job['id'],{'status':'cancelled'});return
                remote=self.google.call(tenant,'calendar','GET','calendars/'+quote(booking['calendar_id'],safe='')+'/events/'+booking['event_id'])
                try:same_start=datetime.fromisoformat(remote.json().get('start',{}).get('dateTime','').replace('Z','+00:00'))==datetime.fromisoformat(booking['starts_at'])
                except (ValueError,TypeError):same_start=False
                if remote.status_code!=200 or remote.json().get('status')!='confirmed' or not same_start:
                    self.store.update('jobs',tenant,job['id'],{'status':'cancelled','error_code':'stale_event'});return
            row=self.google.row(tenant,'gmail')
            if not row or row['state']!='connected':return
            with self.store.transaction():
                current=self.store.get('jobs',tenant,job['id'])
                if current['status']!='pending':return
                self.store.update('jobs',tenant,job['id'],{'status':'sending','attempts':current['attempts']+1})
            message=EmailMessage();message['From']=row['account'];message['To']=job['recipient'];message['Subject']=job['subject'];message['Message-ID']='<'+sha256((tenant+job['id']).encode()).hexdigest()+'@ontelyx.tech>'
            message.set_content(self.secrets.get(tenant,'concierge:mail:'+job['id']))
            if job.get('booking_id') and datetime.fromisoformat(booking['starts_at'])<=self.clock():
                self.store.update('jobs',tenant,job['id'],{'status':'cancelled'});return
            response=self.google.call(tenant,'gmail','POST','users/me/messages/send',json={'raw':base64.urlsafe_b64encode(message.as_bytes()).decode()})
            if response.status_code!=200 or not response.json().get('id'):raise DomainError('delivery_unknown',503)
            self.store.update('jobs',tenant,job['id'],{'status':'sent','google_message_id':response.json()['id'],'sent_at':self.clock().isoformat()})
        except DomainError as error:
            if error.code=='provider_rate_limited' and job['attempts']+1<3:
                self.store.update('jobs',tenant,job['id'],{'status':'pending','error_code':error.code,'due_at':(self.clock()+timedelta(minutes=2**min(job['attempts']+1,3))).isoformat()});return
            # Gmail has no idempotency-key contract: uncertain sends are never replayed.
            self.store.update('jobs',tenant,job['id'],{'status':'delivery_unknown' if error.code in ('delivery_unknown','provider_error') else 'blocked','error_code':error.code})
