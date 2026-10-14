"""Small provider-shaped offline responses used only by the explicitly enabled local service."""
from urllib.parse import parse_qs
import httpx
from .connector_adapters import PROFILES, ACTION_SCOPES,required_scopes

def fixture_transport():
    counters={};contacts={}
    def handle(request):
        path=request.url.path;data=parse_qs(request.content.decode()) if request.headers.get('content-type','').startswith('application/x-www-form-urlencoded') else {}
        provider=next((p for p,profile in PROFILES.items() if str(request.url)==profile['token']),None)
        if provider:
            counters[provider]=counters.get(provider,0)+1
            scopes=required_scopes(provider,list(ACTION_SCOPES[provider]))
            return httpx.Response(200,json={'access_token':'fixture-access-'+str(counters[provider]),'refresh_token':'fixture-refresh-'+str(counters[provider]),'expires_in':3600,'scope':' '.join(scopes),'scopes':scopes})
        if path.endswith('/userinfo'):return httpx.Response(200,json={'email':'fixture-owner@example.invalid','email_verified':True})
        if path=='/v1.0/me':return httpx.Response(200,json={'id':'fixture-account'})
        if path=='/users/me':return httpx.Response(200,json={'resource':{'uri':'https://api.calendly.com/users/fixture-account'}})
        if path.endswith('/introspect'):return httpx.Response(200,json={'active':True,'hub_id':123})
        if path.endswith('/calendarList'):return httpx.Response(200,json={'items':[{'id':'fixture-primary','accessRole':'owner'}]})
        if path.endswith('/calendars'):return httpx.Response(200,json={'value':[{'id':'fixture-primary','canEdit':True}]})
        if path=='/event_types':return httpx.Response(200,json={'collection':[{'uri':'fixture-primary'}]})
        if path=='/crm/v3/properties/contacts':return httpx.Response(200,json={'results':[{'name':'email'},{'name':'firstname'},{'name':'company'}]})
        if path.startswith('/crm/v3/objects/contacts/') and request.method=='GET':
            if path.endswith('/fixture-primary'):return httpx.Response(200,json={'id':'fixture-contact'})
            email=request.url.path.rsplit('/',1)[-1]
            return httpx.Response(200,json=contacts[email]) if email in contacts else httpx.Response(404,json={})
        if path=='/crm/v3/objects/contacts' and request.method=='POST':
            properties=__import__('json').loads(request.content)['properties'];email=properties['email']
            contacts[email]={'id':'fixture-contact','properties':properties}
            return httpx.Response(201,json=contacts[email])
        if path.endswith('/freeBusy'):return httpx.Response(200,json={'calendars':{'fixture-primary':{'busy':[]}}})
        if path.endswith('/getSchedule'):return httpx.Response(200,json={'value':[{'scheduleId':'fixture-primary','scheduleItems':[]}]})
        if path=='/event_type_available_times':return httpx.Response(200,json={'collection':[{'start_time':'2030-10-09T12:00:00Z'}]})
        if request.method=='DELETE':return httpx.Response(204)
        if request.method in ('POST','PATCH'):return httpx.Response(200,json={'id':'fixture-event','etag':'fixture-etag'})
        return httpx.Response(200,json={'collection':[],'value':[]})
    return httpx.MockTransport(handle)
