"""Bounded bidirectional media loop. Slow STT/agents/tools never run on its reader."""
import asyncio
import base64
from hashlib import sha256
from concurrent.futures import ThreadPoolExecutor
from time import monotonic
from pydantic import ValidationError
from .audio import TurnBuffer
from .domain import AudioFrame, RecognitionResult, DomainError
from .voice import TERMINAL
from .language import tr
from .observability import correlation_id


class WebSocketAudioTransport:
    def __init__(self, websocket, *, twilio=False, stream_sid=None):
        self.websocket, self.twilio, self.stream_sid = websocket, twilio, stream_sid
        self.lock = asyncio.Lock()

    async def receive(self):
        import json
        raw = await self.websocket.receive_text()
        if len(raw) > 65536:
            raise DomainError('invalid_input', 413)
        try:
            value = json.loads(raw)
            if not isinstance(value, dict): raise ValueError()
            return value
        except ValueError:
            raise DomainError('invalid_input', 422) from None

    async def send_audio(self, payload, *, encoding, turn_id):
        event = {'event': 'media' if self.twilio else 'audio', 'media': {'payload': base64.b64encode(payload).decode()}}
        if self.twilio:
            if encoding != 'mulaw':
                raise DomainError('unsupported_audio', 422)
            event['streamSid'] = self.stream_sid
        else:
            event.update(encoding=encoding, turn_id=turn_id, speech_validated=False)
        async with self.lock: await self.websocket.send_json(event)

    async def clear(self):
        event = {'event': 'clear'}
        if self.twilio: event['streamSid'] = self.stream_sid
        async with self.lock: await self.websocket.send_json(event)

    async def send_event(self, event):
        if self.twilio:
            return  # Twilio only accepts media/mark/clear, not application diagnostics.
        async with self.lock: await self.websocket.send_json(event)

    async def close(self):
        try: await self.websocket.close()
        except (RuntimeError, OSError): pass


class VoiceRuntime:
    def __init__(self, manager):
        self.manager = manager
        self.pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix='voice-worker')
        self.active_sessions, self.queue_depths = set(), {}

    def gauges(self, tenant):
        operations = self.manager.store.operations
        if operations:
            operations.gauge(tenant, 'active_voice_sessions', sum(owner == tenant for owner, _ in self.active_sessions))
            operations.gauge(tenant, 'audio_queue_depth', sum(size for (owner, _), size in self.queue_depths.items() if owner == tenant))

    async def threaded(self, function, *args, **kwargs):
        from functools import partial
        return await asyncio.get_running_loop().run_in_executor(self.pool, partial(function, *args, **kwargs))

    def shutdown(self):
        self.pool.shutdown(wait=True, cancel_futures=True)

    async def run(self, principal, call, transport):
        manager = self.manager
        config = await self.threaded(manager.config, principal.tenant_id, call['assistant_id'])
        call_timeout = min(config.call_timeout_seconds, call.get('budget_seconds', config.call_timeout_seconds))
        queue = asyncio.Queue(maxsize=4)
        buffer = TurnBuffer(max_seconds=config.max_utterance_seconds, silence_ms=config.turn_silence_ms)
        pending, queued_at, submitted = {}, {}, set()
        received_utterances = set()
        started, last_activity = monotonic(), monotonic()
        packet_window, packet_count = monotonic(), 0
        epoch, playing, processing, closed, utterance = 0, False, False, False, 0
        active_key = (principal.tenant_id, call['id'])
        # Ticket consumption and attachment are atomic; a second stream cannot join.
        def attach():
            with manager.store.transaction():
                current = manager.store.get('call_sessions', principal.tenant_id, call['id'])
                if current['stream_active'] or current['status'] in TERMINAL:
                    raise DomainError('conflict', 409)
                manager.store.update('call_sessions', principal.tenant_id, call['id'], {'stream_active': True})
        await self.threaded(attach)
        self.active_sessions.add(active_key)
        self.queue_depths[active_key] = 0
        self.gauges(principal.tenant_id)

        def turn_correlation(key):
            return sha256((call['id'] + ':' + key).encode()).hexdigest()[:32]

        def trace(stage, key, **fields):
            if manager.store.operations:
                manager.store.operations.trace_voice(principal.tenant_id, stage, turn_correlation(key),
                    call_id=call['id'], utterance_id=key, **fields)

        async def play_cached(kind, request_epoch, turn_id, finalized_at=None):
            nonlocal playing,last_activity
            audio=manager.cached_prompts.get((config.tts_provider,call['voice_locale'],
                config.voices[call['voice_locale']],kind))
            if not audio or closed or request_epoch!=epoch: return
            playing=True
            try:
                for offset in range(0,len(audio),160):
                    if closed or request_epoch!=epoch: break
                    await transport.send_audio(audio[offset:offset+160],encoding='mulaw',turn_id=turn_id)
                    if offset==0 and finalized_at is not None and manager.store.operations:
                        manager.store.operations.observe('utterance_to_ack_first_packet',principal.tenant_id,
                            duration_ms=(monotonic()-finalized_at)*1000)
                    await asyncio.sleep(.02)
            finally:
                playing=False
                if request_epoch==epoch: last_activity=monotonic()

        async def play(text, turn_id, snapshot, deadline=None, finalized_at=None):
            nonlocal playing,last_activity
            current_epoch = epoch
            limit = config.max_latency_ms / 1000 if deadline is None else max(.001, deadline - monotonic())
            playing = True
            try:
                synthesis_started = monotonic()
                audio, encoding = await asyncio.wait_for(self.threaded(manager.speak, snapshot, text), limit)
                trace('tts_completed', turn_id, duration_ms=(monotonic()-synthesis_started)*1000)
                if current_epoch != epoch or closed: return
                await self.threaded(manager.record_audio, principal, snapshot, audio, encoding, 8000, 'assistant')
                if deadline is not None and monotonic() > deadline: raise asyncio.TimeoutError()
                step = 160 if encoding == 'mulaw' else max(1, len(audio))
                for offset in range(0, len(audio), step):
                    if closed or current_epoch != epoch: break
                    await transport.send_audio(audio[offset:offset + step], encoding=encoding, turn_id=turn_id)
                    if offset == 0:
                        trace('output_packet_sent', turn_id, duration_ms=(monotonic()-finalized_at)*1000 if finalized_at else 0)
                    if offset == 0 and finalized_at is not None and manager.store.operations:
                        manager.store.operations.observe('utterance_final_to_first_output_packet', principal.tenant_id,
                            duration_ms=(monotonic()-finalized_at)*1000)
                    if encoding == 'mulaw': await asyncio.sleep(.02)
                await transport.send_event({'event': 'audio_done', 'turn_id': turn_id})
            finally:
                playing=False
                if current_epoch==epoch: last_activity=monotonic()

        def process_item(item, request_epoch):
            # Re-read membership before speech-provider work, not only at connection time.
            actor = manager.store.principal(principal.subject, principal.tenant_id)
            actor.require('execute')
            snapshot = manager.store.get('call_sessions', principal.tenant_id, call['id'])
            if snapshot['status'] in TERMINAL:
                return snapshot
            if isinstance(item, RecognitionResult):
                text, turn_id = item.text, item.utterance_id
            else:
                sample, encoding, rate, turn_id = item
                manager.record_audio(actor, snapshot, sample, 'fixture_utf8' if encoding == 'fixture_utf8' else 'pcm16', rate)
                trace('stt_partial', turn_id, partial_supported=False)
                recognition_started = monotonic()
                text = manager.transcribe(snapshot, sample, encoding, rate)
                trace('stt_final', turn_id, transcript_present=bool(text.strip()), duration_ms=(monotonic()-recognition_started)*1000)
            if request_epoch != epoch: raise DomainError('generation_cancelled', 409)
            if not text.strip(): return {**snapshot,'ignored_utterance':True}
            return manager.process_text(actor, call['id'], text, turn_id)

        def process(item, request_epoch):
            key = item.utterance_id if isinstance(item, RecognitionResult) else item[3]
            token = correlation_id.set(turn_correlation(key))
            try:
                return process_item(item, request_epoch)
            finally:
                correlation_id.reset(token)

        async def worker():
            nonlocal closed, call, failure, processing
            await play(call['last_response'], 'greeting', call)
            while not closed:
                key = await queue.get()
                acknowledgement=None
                try:
                    # Final hypotheses may be corrected before this short settling window.
                    await asyncio.sleep(.1)
                    item = pending.pop(key)
                    deadline = queued_at.pop(key) + config.max_latency_ms / 1000
                    finalized_at = deadline - config.max_latency_ms / 1000
                    submitted.add(key)
                    request_epoch = epoch
                    processing = True
                    if deadline <= monotonic(): raise asyncio.TimeoutError()
                    async def acknowledge():
                        await asyncio.sleep(6)
                        if processing: await play_cached('wait',request_epoch,'wait:'+key,finalized_at)
                    acknowledgement=asyncio.create_task(acknowledge())
                    response = await asyncio.wait_for(self.threaded(process, item, request_epoch), deadline - monotonic())
                    acknowledgement.cancel()
                    await asyncio.gather(acknowledgement,return_exceptions=True)
                    processing = False
                    call = response
                    await transport.send_event({'event': 'turn_result', 'utterance_id': key,
                        'status': call['status'], 'locale': call['voice_locale'], 'response': '' if call.get('ignored_utterance') else call.get('last_response', ''),
                        'duplicate': call.get('duplicate', False), 'state': call['state']})
                    if call['status'] in TERMINAL:
                        closed = True
                        await transport.close()
                    elif call.get('last_response') and not call.get('duplicate') and not call.get('ignored_utterance') and request_epoch == epoch:
                        await play(call['last_response'], key, call, deadline, finalized_at)
                except (DomainError, asyncio.TimeoutError) as exc:
                    code = exc.code if isinstance(exc, DomainError) else 'timeout'
                    if request_epoch!=epoch: continue
                    if code == 'timeout': manager.providers.cancel_llm(principal.tenant_id, call['id'])
                    if code == 'generation_cancelled': continue
                    await transport.send_event({'event': 'error', 'code': code, 'message': tr(call['voice_locale'], code)})
                    if acknowledgement:
                        acknowledgement.cancel()
                        await asyncio.gather(acknowledgement,return_exceptions=True)
                    await play_cached('slow',request_epoch,'failure:'+key)
                    if code in ('provider_error', 'timeout', 'forbidden', 'unauthorized', 'disabled'):
                        failure = code
                        closed = True
                        await transport.close()
                    # Never automatically replay a failed or timed-out business action.
                finally:
                    if acknowledgement:
                        acknowledgement.cancel()
                        await asyncio.gather(acknowledgement,return_exceptions=True)
                    processing = False
                    queue.task_done()
                    self.queue_depths[active_key] = queue.qsize()
                    self.gauges(principal.tenant_id)

        failure = None
        async def supervised_worker():
            nonlocal closed, failure
            try:
                await worker()
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failure = exc.code if isinstance(exc, DomainError) else 'provider_error'
                closed = True
                await transport.send_event({'event': 'error', 'code': failure, 'message': tr(call['voice_locale'], failure)})
                await transport.close()
        task = asyncio.create_task(supervised_worker())
        try:
            while not closed:
                call_remaining=call_timeout-(monotonic()-started)
                remaining=call_remaining if playing or processing else min(call_remaining,
                    config.silence_timeout_seconds-(monotonic()-last_activity))
                if remaining <= 0:
                    raise DomainError('timeout', 408)
                try: event = await asyncio.wait_for(transport.receive(), remaining)
                except asyncio.TimeoutError:
                    if (playing or processing) and monotonic() - started < call_timeout:
                        last_activity = monotonic()
                        continue
                    raise DomainError('timeout', 408) from None
                if monotonic() - packet_window >= 1:
                    packet_window, packet_count = monotonic(), 0
                packet_count += 1
                if packet_count > 200:
                    raise DomainError('rate_limited', 429)
                kind = event.get('event')
                if kind == 'ping':
                    await transport.send_event({'event': 'pong'})
                    continue
                if kind in ('stop', 'disconnect'):
                    break
                if kind == 'barge_in':
                    epoch += 1
                    manager.providers.cancel_llm(principal.tenant_id, call['id'])
                    playing = False
                    await transport.clear()
                    continue
                if kind == 'mark': continue
                if kind == 'recognition' and not transport.twilio:
                    recognition = RecognitionResult.model_validate({key: value for key, value in event.items() if key != 'event'})
                    if call['provider'] != 'mock': raise DomainError('forbidden', 403)
                    if not recognition.final:
                        await transport.send_event({'event': 'partial_ignored', 'utterance_id': recognition.utterance_id})
                        continue
                    item, active = recognition, bool(recognition.text)
                    key = recognition.utterance_id
                elif kind == 'media':
                    if getattr(transport, 'rtp', False):
                        frame = AudioFrame(sequence=event['sequence'], utterance_id='rtp:' + str(utterance),
                            payload=event['payload'], encoding='mulaw', sample_rate=8000)
                    elif transport.twilio:
                        if event.get('streamSid') != transport.stream_sid:
                            raise DomainError('forbidden', 403)
                        frame = AudioFrame(sequence=int(event['sequenceNumber']), utterance_id='media:' + str(utterance),
                                           payload=event['media']['payload'], encoding='mulaw', sample_rate=8000)
                    else:
                        frame = AudioFrame.model_validate(event.get('frame', {}))
                    if frame.utterance_id not in received_utterances:
                        received_utterances.add(frame.utterance_id)
                        trace('audio_received', frame.utterance_id, sample_rate=frame.sample_rate)
                    item, active = buffer.feed(frame)
                    if item is None:
                        if active:
                            last_activity = monotonic()
                            if playing or processing:
                                epoch += 1
                                manager.providers.cancel_llm(principal.tenant_id, call['id'])
                                playing = False
                                await transport.clear()
                        continue
                    key = item[3]
                    trace('vad_final', key, sample_rate=item[2], audio_ms=len(item[0])*1000/(2*item[2]))
                    utterance += 1
                else:
                    raise DomainError('invalid_input', 422)
                last_activity = monotonic()
                if active and (playing or processing):
                    epoch += 1
                    manager.providers.cancel_llm(principal.tenant_id, call['id'])
                    playing = False
                    await transport.clear()
                if key in submitted:
                    await transport.send_event({'event': 'correction_ignored', 'utterance_id': key})
                    continue
                if key not in pending:
                    try: queue.put_nowait(key)
                    except asyncio.QueueFull: raise DomainError('limit_reached', 429) from None
                    queued_at[key] = monotonic()
                    self.queue_depths[active_key] = queue.qsize()
                    self.gauges(principal.tenant_id)
                pending[key] = item
        except (DomainError, ValidationError, ValueError, KeyError) as exc:
            failure = exc.code if isinstance(exc, DomainError) else 'invalid_input'
            await transport.send_event({'event': 'error', 'code': failure, 'message': tr(call['voice_locale'], failure)})
        except Exception:
            # Includes graceful peer disconnect; never echo transport exception text.
            pass
        finally:
            closed = True
            epoch += 1
            manager.providers.cancel_llm(principal.tenant_id, call['id'])
            buffer.reset()
            pending.clear()
            queued_at.clear()
            self.active_sessions.discard(active_key)
            self.queue_depths.pop(active_key, None)
            self.gauges(principal.tenant_id)
            # Submit terminal persistence before any cancellable socket await.
            cleanup = self.pool.submit(manager.finish, principal, call['id'], 'failed' if failure else 'ended', failure)
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            await transport.close()
            # A synchronous in-flight worker cannot be killed safely. No retry is
            # performed; its transaction finishes before terminal state is persisted.
            await asyncio.shield(asyncio.wrap_future(cleanup))
