"""Private Asterisk ExternalMedia RTP/PCMU transport for the existing voice runtime."""
import asyncio
import base64
import secrets
import struct
from time import monotonic
from .domain import DomainError


class RTPDecoder:
    def __init__(self): self.ssrc, self.sequence, self.extended = None, None, 0

    def decode(self, packet):
        if not 12 <= len(packet) <= 1200: raise DomainError('unsupported_audio', 422)
        first, second, sequence, _, ssrc = struct.unpack('!BBHII', packet[:12])
        if first >> 6 != 2 or second & 127 != 0: raise DomainError('unsupported_audio', 422)
        offset = 12 + (first & 15)*4
        if offset > len(packet): raise DomainError('unsupported_audio', 422)
        if first & 16:
            if offset+4 > len(packet): raise DomainError('unsupported_audio', 422)
            length = struct.unpack('!H', packet[offset+2:offset+4])[0]
            offset += 4+length*4
        end = len(packet)
        if first & 32:
            padding = packet[-1]
            if not padding or padding > end-offset: raise DomainError('unsupported_audio', 422)
            end -= padding
        payload = packet[offset:end]
        if len(payload) != 160: raise DomainError('unsupported_audio', 422)
        if self.ssrc is not None and self.ssrc != ssrc: raise DomainError('forbidden', 403)
        if self.sequence is not None:
            distance = (sequence-self.sequence) & 65535
            if distance == 0 or distance > 32767: return None
            if distance > 100: raise DomainError('unsupported_audio', 422)
        self.ssrc, self.sequence = ssrc, sequence
        self.extended += 1
        return self.extended, payload


class RTPAudioTransport(asyncio.DatagramProtocol):
    twilio, rtp = False, True

    def __init__(self, *, operations=None, tenant_id=''):
        self.queue, self.decoder = asyncio.Queue(maxsize=128), RTPDecoder()
        self.socket, self.peer, self.closed = None, None, False
        self.operations, self.tenant_id = operations, tenant_id
        self.sequence, self.timestamp, self.ssrc = secrets.randbelow(65536), secrets.randbits(32), secrets.randbits(32)

    def connection_made(self, transport): self.socket = transport

    def datagram_received(self, packet, peer):
        if self.closed or self.peer is None or peer != self.peer: return
        start = monotonic()
        try:
            decoded = self.decoder.decode(packet)
            if decoded:
                sequence, payload = decoded
                self.queue.put_nowait({'event':'media', 'sequence':sequence, 'payload':base64.b64encode(payload).decode()})
                if self.operations: self.operations.observe('rtp_ingestion', self.tenant_id, duration_ms=(monotonic()-start)*1000)
        except (DomainError, asyncio.QueueFull):
            # Fail closed on malformed negotiated media/backpressure; never grow buffers.
            self.closed = True
            while not self.queue.empty(): self.queue.get_nowait()
            self.queue.put_nowait({'event':'transport_error', 'code':'unsupported_audio'})
            if self.operations: self.operations.observe('rtp_failure', self.tenant_id, error='unsupported_audio')

    async def receive(self):
        event = await self.queue.get()
        if event['event'] == 'transport_error': raise DomainError(event['code'], 422)
        return event

    async def send_audio(self, payload, *, encoding, turn_id):
        if self.closed: return
        if encoding != 'mulaw' or not self.peer or not 0 < len(payload) <= 160: raise DomainError('unsupported_audio', 422)
        payload = payload.ljust(160, b'\xff')
        packet = struct.pack('!BBHII', 128, 0, self.sequence, self.timestamp, self.ssrc)+payload
        self.socket.sendto(packet, self.peer)
        self.sequence = (self.sequence+1) & 65535
        self.timestamp = (self.timestamp+160) & 0xffffffff

    async def clear(self): pass  # No playback queue here; runtime stops paced packets by epoch.

    async def send_event(self, event):
        if event.get('event') == 'error' and self.operations:
            self.operations.observe('rtp_voice_error', self.tenant_id, error=event.get('code', 'provider_error'))

    async def close(self):
        self.closed = True
        if self.socket: self.socket.close()
        while not self.queue.empty(): self.queue.get_nowait()
        self.queue.put_nowait({'event':'disconnect'})
