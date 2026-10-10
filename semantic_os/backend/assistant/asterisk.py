"""ARI control only. SIP signaling stays in Asterisk; audio uses the existing VoiceRuntime."""
import asyncio
from dataclasses import dataclass
from ipaddress import ip_address
import json
from urllib.parse import quote, urlencode, urlsplit
import httpx
from .domain import Capability, DomainError
from .rtp import RTPAudioTransport
from .store import uid


@dataclass(frozen=True)
class ARISettings:
    endpoint: str
    username: str
    password: str
    tenant_id: str
    assistant_id: str
    service_subject: str
    advertised_host: str
    asterisk_rtp_host: str
    bind_host: str = '0.0.0.0'
    extension: str = '2000'
    caller_endpoint: str = '1001'
    application: str = 'testmid-voice'

    def validate(self):
        url = urlsplit(self.endpoint)
        if url.scheme not in ('http', 'https') or url.username or url.password or url.query or url.fragment or url.path.rstrip('/') != '/ari':
            raise DomainError('invalid_input', 422)
        for value in (url.hostname, self.advertised_host, self.asterisk_rtp_host):
            try:
                if not ip_address(value).is_private or ip_address(value).is_unspecified: raise ValueError()
            except ValueError: raise DomainError('invalid_input', 422) from None
        if not self.username or len(self.password) < 24 or not self.extension.isdigit() or not self.caller_endpoint.isdigit():
            raise DomainError('unconfigured', 503)


class AsteriskTelephonyProvider:
    capability = Capability('asterisk', 'LIVE_UNVERIFIED', features=('ari_external_media',), limitations=('live_sip_unverified',))
    def start(self, call_id, locale): return {'provider':'asterisk', 'status':'listening', 'call_id':call_id}
    def terminate(self, call_id): return {'provider':'asterisk', 'status':'ended', 'call_id':call_id}
    def transfer(self, call_id, destination): raise DomainError('unconfigured', 503)


class ARIBridge:
    def __init__(self, settings, manager, runtime, *, client=None):
        settings.validate()
        self.settings, self.manager, self.runtime = settings, manager, runtime
        self.client = client or httpx.AsyncClient(base_url=settings.endpoint.rstrip('/')+'/', auth=(settings.username, settings.password), timeout=10, follow_redirects=False)
        self.sessions, self.tasks, self.resources, self.call_ids, self.pending, self.stopping = {}, set(), {}, {}, set(), False
        self.loop=None
        manager.ari_bridge=self

    def close_for_call(self, tenant_id, call_id):
        if tenant_id!=self.settings.tenant_id or not self.loop or self.loop.is_closed(): return
        for channel, identifier in list(self.call_ids.items()):
            if identifier==call_id and channel in self.sessions:
                asyncio.run_coroutine_threadsafe(self.sessions[channel].close(),self.loop)

    async def request(self, method, path, **params):
        response = await self.client.request(method, path, params=params)
        if response.status_code not in (200, 201, 204): raise DomainError('provider_error', 502)
        return response.json() if response.content else {}

    async def remove(self, path):
        try:
            response = await self.client.delete(path, timeout=2)  # Only generated/tracked resources and accepted caller channels.
            if response.status_code not in (200, 204, 404) and self.manager.store.operations:
                self.manager.store.operations.observe('ari_cleanup', self.settings.tenant_id, error='provider_error')
        except httpx.HTTPError:
            self.manager.store.operations.observe('ari_cleanup', self.settings.tenant_id, error='provider_error')

    async def journey(self, channel_id):
        cfg, transport, call = self.settings, RTPAudioTransport(operations=self.manager.store.operations, tenant_id=self.settings.tenant_id), None
        external, bridge = 'testmid-media-'+uid(), 'testmid-bridge-'+uid()
        self.sessions[channel_id] = transport
        self.resources[channel_id] = (external, bridge)
        actor = None
        try:
            actor = await self.runtime.threaded(self.manager.store.principal, cfg.service_subject, cfg.tenant_id)
            actor.require('execute')
            assistant = await self.runtime.threaded(self.manager.store.get, 'assistants', cfg.tenant_id, cfg.assistant_id)
            if assistant['llm_provider'] != 'qwen': raise DomainError('unconfigured', 503)
            loop = asyncio.get_running_loop()
            self.loop=loop
            await loop.create_datagram_endpoint(lambda: transport, local_addr=(cfg.bind_host, 0))
            port = transport.socket.get_extra_info('sockname')[1]
            await self.request('POST', 'bridges/'+bridge, type='mixing,proxy_media')
            await self.request('POST', 'channels/externalMedia', app=cfg.application, external_host=f'{cfg.advertised_host}:{port}',
                format='ulaw', channelId=external, encapsulation='rtp', transport='udp', connection_type='client', direction='both')
            address = await self.request('GET', 'channels/'+external+'/variable', variable='UNICASTRTP_LOCAL_ADDRESS')
            local_port = await self.request('GET', 'channels/'+external+'/variable', variable='UNICASTRTP_LOCAL_PORT')
            if address.get('value') != cfg.asterisk_rtp_host: raise DomainError('forbidden', 403)
            peer_port = int(local_port['value'])
            if not 1024 <= peer_port <= 65535: raise DomainError('invalid_input', 422)
            transport.peer = (cfg.asterisk_rtp_host, peer_port)
            call = await self.runtime.threaded(self.manager.start, actor, cfg.assistant_id, None,
                provider_call_id=channel_id, external_key='ari:'+channel_id)
            self.call_ids[channel_id] = call['id']
            if transport.closed: return
            await self.request('POST', 'channels/'+quote(channel_id, safe='')+'/answer')
            await self.request('POST', 'bridges/'+bridge+'/addChannel', channel=channel_id+','+external)
            await self.runtime.run(actor, call, transport)
        except (DomainError, httpx.HTTPError, ValueError, KeyError):
            if call and actor: await self.runtime.threaded(self.manager.finish, actor, call['id'], 'failed', 'provider_error')
            if self.manager.store.operations: self.manager.store.operations.observe('ari_call', cfg.tenant_id, error='provider_error')
        finally:
            await transport.close()
            if call:
                self.manager.providers.cancel_llm(cfg.tenant_id, call['id'])
                if actor: await self.runtime.threaded(self.manager.finish, actor, call['id'])
            for path in ('channels/'+external, 'bridges/'+bridge, 'channels/'+quote(channel_id, safe='')): await self.remove(path)
            self.sessions.pop(channel_id, None)
            self.resources.pop(channel_id, None)
            self.call_ids.pop(channel_id, None)
            self.pending.discard(channel_id)

    async def event(self, event):
        if event.get('application') != self.settings.application: return
        channel = event.get('channel', {})
        id = channel.get('id', '')
        if not isinstance(id, str) or not 0 < len(id) <= 200: return
        if event.get('type') in ('StasisEnd', 'ChannelDestroyed') and id in self.sessions:
            await self.sessions[id].close()
            # Cancel by provider ID without waiting on the database audio/model transaction.
            if id in self.call_ids: self.manager.providers.cancel_llm(self.settings.tenant_id, self.call_ids[id])
        elif event.get('type') == 'StasisStart':
            if id.startswith('testmid-media-') or id in self.pending or self.stopping: return
            if channel.get('dialplan', {}).get('exten') != self.settings.extension or not channel.get('name', '').startswith('PJSIP/'+self.settings.caller_endpoint+'-'): return
            if len(self.tasks) >= 4:
                await self.remove('channels/'+quote(id, safe='')); return
            self.pending.add(id)
            task = asyncio.create_task(self.journey(id))
            self.tasks.add(task)
            task.add_done_callback(self.tasks.discard)

    async def run(self):
        from websockets.asyncio.client import connect
        url = self.settings.endpoint.rstrip('/')+'/events?'+urlencode({'app':self.settings.application})
        url = url.replace('http://','ws://',1).replace('https://','wss://',1)
        import base64
        header = 'Basic '+base64.b64encode((self.settings.username+':'+self.settings.password).encode()).decode()
        # No transparent reconnect/replayed actions. Operator restarts after inspecting failure.
        async with connect(url, additional_headers={'Authorization':header}, max_size=65536, max_queue=16, open_timeout=10) as socket:
            self.manager.store.operations.worker['ari_status'] = 'connected_unverified'
            async for raw in socket:
                value = json.loads(raw)
                if not isinstance(value, dict): raise DomainError('invalid_input', 422)
                await self.event(value)

    async def close(self):
        self.stopping = True
        for transport in list(self.sessions.values()): await transport.close()
        for call_id in list(self.call_ids.values()): self.manager.providers.cancel_llm(self.settings.tenant_id, call_id)
        if self.tasks: await asyncio.gather(*list(self.tasks), return_exceptions=True)
        await self.client.aclose()
