"""Tenant-scoped call lifecycle. The existing orchestrator remains the only agent runtime."""
from datetime import datetime, timedelta
from hashlib import sha256
import json
from .domain import DomainError, Incoming, VoiceConfig, Principal
from .booking import explicit_confirmation
from .language import tr, LanguageResolver
from .store import uid
from .observability import timed, correlation_id

TERMINAL = {'ended', 'transferred', 'failed'}
TRANSITIONS = {
    'listening': {'speak': 'speaking', 'terminate': 'ended', 'transfer': 'transferred', 'language': 'listening', 'transcript': 'listening'},
    'speaking': {'barge_in': 'listening', 'finish_speaking': 'listening', 'terminate': 'ended', 'transfer': 'transferred', 'language': 'listening', 'transcript': 'listening'},
}


class VoiceSessionManager:
    def __init__(self, store, providers, orchestrator):
        self.store, self.providers, self.orchestrator = store, providers, orchestrator
        self.clock = orchestrator.clock
        self.gateway = None
        self.cached_prompts = {}

    def warm_local_prompts(self):
        """Deployment-owned generic audio only; no tenant text or synthetic business outcome."""
        engine=self.providers.local_tts
        if engine is None: return
        phrases={'bg-BG':{'wait':'Моля, изчакайте за момент.',
                          'slow':'Обработката се забави. Моля, опитайте отново след малко.'},
                 'en-US':{'wait':'Please wait a moment.',
                          'slow':'Processing is taking too long. Please try again shortly.'}}
        for locale, prompts in phrases.items():
            voice=engine.voice_ids[locale]
            for kind,text in prompts.items():
                audio=engine.synthesize(text,locale,voice)
                if not audio or len(audio)>8*8000: raise DomainError('invalid_model_output',502)
                self.cached_prompts[(engine.capability.provider,locale,voice,kind)]=audio

    def config(self, tenant_id, assistant_id):
        return VoiceConfig.model_validate(self.store.get('assistants', tenant_id, assistant_id).get('voice_settings', {}))

    def services(self, call):
        if call.get('connection_id'):
            return self.gateway.services(self.store.get('channel_connections', call['tenant_id'], call['connection_id']))
        cfg = self.config(call['tenant_id'], call['assistant_id'])
        if cfg.telephony_provider=='asterisk' and cfg.stt_provider=='faster_whisper' and cfg.tts_provider in ('piper','espeak_ng','bgtts38'):
            services = (self.providers.asterisk, self.providers.local_stt, self.providers.local_tts)
            if any(service is None for service in services): raise DomainError('unconfigured', 503)
            return services
        if (cfg.telephony_provider, cfg.stt_provider, cfg.tts_provider) != ('mock', 'mock', 'mock'):
            raise DomainError('unconfigured', 503)
        return self.providers.telephony, self.providers.speech, self.providers.speech

    def record_event(self, principal, call, action, code=None):
        self.store.add('call_events', principal.tenant_id, {'conversation_id': call['conversation_id'],
            'call_id': call['id'], 'action': action, 'status': call['status'], 'locale': call['voice_locale'],
            'timestamp': self.clock().isoformat(), 'error_code': code})
        self.store.audit(principal, 'call:' + action, resource_id=call['id'], status=code or 'completed')

    def start(self, principal, assistant_id, locale=None, *, recording=False, transcript_storage=False,
              caller='anonymous', provider_call_id=None, connection_id=None, external_key=None, consent_given=False):
        principal.require('execute')
        assistant = self.store.get('assistants', principal.tenant_id, assistant_id)
        cfg = self.config(principal.tenant_id, assistant_id)
        if cfg.telephony_provider=='asterisk' and not provider_call_id: raise DomainError('unconfigured',503)
        active_locale = locale or cfg.locale
        tenant = self.store.tenant(principal.tenant_id)
        if recording and not cfg.recording or transcript_storage and not cfg.transcript_storage:
            raise DomainError('forbidden', 403)
        if (recording and not tenant['recording_enabled'] or transcript_storage and not tenant['transcripts_enabled']
                or (recording or transcript_storage) and (not consent_given or cfg.lawful_basis == 'none')):
            raise DomainError('forbidden', 403)
        if (recording or transcript_storage) and (not self.gateway or not self.gateway.secrets.cipher):
            raise DomainError('unconfigured', 503)
        context = {'tenant_id': principal.tenant_id, 'assistant_id': assistant_id, 'connection_id': connection_id}
        telephony, stt, tts = self.services(context)
        stt.require(active_locale)
        if active_locale not in tts.capability.locales:
            raise DomainError('unsupported_locale', 422)
        if hasattr(tts, 'voice_ids') and cfg.voices.get(active_locale) != tts.voice_ids.get(active_locale):
            raise DomainError('unsupported_locale', 422)
        with self.store.transaction():
            active = [c for c in self.store.list('call_sessions', principal.tenant_id) if c['status'] not in TERMINAL]
            call_budget = cfg.call_timeout_seconds
            if self.store.entitlements:
                self.store.entitlements.check(principal.tenant_id, 'voice_seconds', 1)
                remaining = self.store.entitlements.remaining(principal.tenant_id, 'voice_seconds')
                reserved = sum(c.get('budget_seconds', cfg.call_timeout_seconds) for c in active)
                if remaining is not None:
                    if remaining - reserved < 1: raise DomainError('upgrade_required', 402)
                    call_budget = min(call_budget, remaining - reserved)
            if len(active) >= cfg.max_concurrent_calls:
                raise DomainError('limit_reached', 429)
            conversation = self.orchestrator.conversation(principal, assistant_id, 'voice')
            self.store.update('conversations', principal.tenant_id, conversation['id'], {'active_locale': active_locale})
            id = uid()
            self.store.update('conversations', principal.tenant_id, conversation['id'], {'call_session_id': id,
                'voice_confirmation_mode':cfg.booking_confirmation_mode})
            provider_id = provider_call_id or 'mock:' + id
            session = telephony.start(provider_id, active_locale)
            masked = caller if caller == 'anonymous' else caller[:4] + '***' + caller[-3:]
            call = self.store.add('call_sessions', principal.tenant_id, {**session, 'assistant_id': assistant_id,
                'conversation_id': conversation['id'], 'provider_call_id': provider_id, 'connection_id': connection_id,
                'caller_identifier': masked, 'voice_locale': active_locale, 'locale_explicit': locale is not None,
                'owner_user_id': principal.user_id,
                'booking_confirmation_mode':cfg.booking_confirmation_mode,
                'locale_established': False, 'recording_enabled': recording, 'transcript_storage': transcript_storage,
                'transcripts': [], 'events': [{'event': 'start', 'at': self.clock().isoformat()}],
                'started_at': self.clock().isoformat(), 'ended_at': None, 'duration_seconds': 0,
                'last_activity_at': self.clock().isoformat(), 'stream_active': False,
                'last_response': cfg.greetings[active_locale] + ' ' + cfg.privacy_notices[active_locale]
                    + (' ' + cfg.recording_notices[active_locale] if recording or transcript_storage else ''),
                'state': 'MOCK' if telephony.capability.provider == 'mock' else 'LIVE_UNVERIFIED',
                'budget_seconds': call_budget,
                'speech_validated': False, 'error_code': None}, id=id, external_key=external_key)
            for role, identifier in (('caller', masked), ('assistant', assistant_id)):
                self.store.add('call_participants', principal.tenant_id, {'conversation_id': conversation['id'],
                               'call_id': id, 'role': role, 'identifier': identifier})
            self.record_event(principal, call, 'start')
            return call

    @timed('tts_provider')
    def speak(self, call, text):
        _, _, tts = self.services(call)
        cfg = self.config(call['tenant_id'], call['assistant_id'])
        if self.store.entitlements:
            from .saas_domain import UsageEvent
            self.store.entitlements.record(call['tenant_id'], UsageEvent(resource_id=call['id'], category='tts_characters', quantity=len(text),
                unit='character', provider=tts.capability.provider, timestamp=self.clock(), idempotency_key='tts:' + uid()), enforce=True)
        if tts.capability.provider == 'mock':
            return tts.synthesize(text, call['voice_locale'], cfg.voices[call['voice_locale']]), 'fixture_utf8'
        return tts.synthesize(text, call['voice_locale'], cfg.voices[call['voice_locale']]), 'mulaw'

    @timed('stt_provider')
    def transcribe(self, call, sample, encoding, sample_rate):
        _, stt, _ = self.services(call)
        if stt.capability.provider == 'mock':
            if encoding != 'fixture_utf8':
                raise DomainError('unsupported_audio', 422)
            try:
                return stt.transcribe(sample, call['voice_locale'])
            except UnicodeError:
                raise DomainError('invalid_input', 422) from None
        if encoding == 'fixture_utf8':
            raise DomainError('unsupported_audio', 422)
        from .audio import pcm_16khz
        pcm = pcm_16khz(sample, sample_rate)
        if self.store.entitlements:
            from .saas_domain import UsageEvent
            self.store.entitlements.record(call['tenant_id'], UsageEvent(resource_id=call['id'], category='stt_seconds', quantity=(len(pcm) + 31999) // 32000,
                unit='second', provider=stt.capability.provider, timestamp=self.clock(), idempotency_key='stt:' + uid()), enforce=True)
        locale=None if ('language_detection' in stt.capability.features and not call['locale_explicit'] and not call['locale_established']) else call['voice_locale']
        return stt.transcribe(pcm, locale)

    @timed('voice_turn')
    def process_text(self, principal, call_id, text, utterance_id, *, final=True, tool=None, arguments=None):
        principal = self.store.principal(principal.subject, principal.tenant_id)
        principal.require('execute')
        with self.store.transaction():
            call = self.store.get('call_sessions', principal.tenant_id, call_id)
            if not final:
                return {**call, 'partial': True}  # Partial hypotheses never run agents/tools.
            key = 'voice-turn:' + call_id + ':' + utterance_id
            previous = self.store.find('provider_events', principal.tenant_id, key)
            if previous:
                return {**call, 'duplicate': True, 'correction_ignored': previous['fingerprint'] != sha256(text.encode()).hexdigest()}
            if call['status'] in TERMINAL:
                raise DomainError('invalid_transition', 409)
            cfg = self.config(principal.tenant_id, call['assistant_id'])
            switch = {'please continue in english': 'en-US', 'please continue in bulgarian': 'bg-BG',
                      'switch to english': 'en-US', 'speak english': 'en-US', 'премини на английски': 'en-US',
                      'говорете на английски': 'en-US', 'switch to bulgarian': 'bg-BG', 'speak bulgarian': 'bg-BG',
                      'премини на български': 'bg-BG'}
            command = text.casefold().strip(' .!')
            if command in ('i consent to recording', 'съгласен съм със запис', 'съгласна съм със запис'):
                tenant = self.store.tenant(principal.tenant_id)
                if cfg.lawful_basis == 'none' or not self.gateway or not self.gateway.secrets.cipher:
                    raise DomainError('forbidden', 403)
                call = self.store.update('call_sessions', principal.tenant_id, call_id, {
                    'recording_enabled': bool(cfg.recording and tenant['recording_enabled']),
                    'transcript_storage': bool(cfg.transcript_storage and tenant['transcripts_enabled'])})
                result = {'response': cfg.recording_notices[call['voice_locale']]}
                self.record_event(principal, call, 'consent')
            elif command in switch:
                call = self.event(principal, call_id, 'language', locale=switch[command], event_id='language:' + utterance_id)
                result = {'response': tr(call['voice_locale'], 'voice_language_switched')}
                pending_state=self.store.get('conversations',principal.tenant_id,call['conversation_id']).get('booking_state') or {}
                if call.get('booking_confirmation_mode')=='keypad' and pending_state.get('status')=='awaiting_confirmation':
                    result['booking_status']='awaiting_confirmation'
            else:
                if not call['locale_explicit'] and not call['locale_established']:
                    detected, confidence = LanguageResolver().detect(text)
                    if detected and confidence >= .9:
                        self.services(call)[1].require(detected)
                        call = self.store.update('call_sessions', principal.tenant_id, call_id, {'voice_locale': detected})
                locale = call['voice_locale']
                if self.store.operations:
                    self.store.operations.trace_voice(principal.tenant_id, 'locale_selected', correlation_id.get(),
                        call_id=call_id, utterance_id=utterance_id, locale=locale)
                if call.get('transfer_approval_id') and command in ('no', 'не', 'отказ', 'cancel'):
                    approval = self.store.get('approvals', principal.tenant_id, call['transfer_approval_id'])
                    if approval['status'] == 'pending':
                        self.store.update('approvals', principal.tenant_id, approval['id'], {'status': 'cancelled'})
                    call = self.store.update('call_sessions', principal.tenant_id, call_id, {'transfer_approval_id': None})
                    result = {'response': tr(locale, 'voice_transfer_cancelled')}
                elif call.get('transfer_approval_id') and explicit_confirmation(text):
                    self.store.update('approvals', principal.tenant_id, call['transfer_approval_id'], {'locale': locale})
                    result = self.orchestrator.approve(principal, call['transfer_approval_id'])
                    transferred = self.event(principal, call_id, 'transfer', event_id='transfer:' + utterance_id, confirmed=True)
                    call = transferred
                else:
                    import re
                    if not tool and re.search(r'\b(?:human|оператор|човек)\b', text.casefold()):
                        tool, arguments = 'EscalateToHuman', {'reason': tr(locale, 'voice_human_request')}
                    result = self.orchestrator.inbound(principal, call['conversation_id'], Incoming(
                        content=text, event_id='voice:' + call_id + ':' + utterance_id,
                        locale=locale, tool=tool, arguments=arguments or {}),
                        message_context={'relative_date_reference_at':datetime.fromisoformat(call['started_at']),'provider':call['provider']})
                    if result.get('approval') and result['approval']['tool'] == 'EscalateToHuman':
                        call = self.store.update('call_sessions', principal.tenant_id, call_id, {'transfer_approval_id': result['approval']['id']})
            if result.get('booking_status')=='awaiting_confirmation':
                state=self.store.get('conversations',principal.tenant_id,call['conversation_id'])['booking_state']
                from .language import format_date
                prompt='voice_keypad_proposal' if call.get('booking_confirmation_mode')=='keypad' else 'voice_booking_confirm'
                result['response']=tr(call['voice_locale'],prompt,name=state['contact_name'],
                    date=format_date(state['starts_at'],call['voice_locale'],state['timezone']),duration=state['duration_minutes'])
                if result.get('confirmation_unclear'):
                    result['response']=tr(call['voice_locale'],'booking_confirmation_unclear')+' '+result['response']
            elif result.get('booking_status')=='unavailable' and (result.get('outcome') or {}).get('data',{}).get('available_slots'):
                from .language import format_date
                slots=result['outcome']['data']['available_slots']
                timezone=self.store.tenant(principal.tenant_id)['timezone']
                result['response']=tr(call['voice_locale'],'booking_unavailable')+' '+tr(call['voice_locale'],
                    'booking_alternatives',slots=format_date(slots[0],call['voice_locale'],timezone))
            changes = {'last_response': result['response'], 'last_activity_at': self.clock().isoformat(),
                       'locale_established': True, 'status': call['status'] if call['status'] in TERMINAL else 'listening'}
            if call.get('booking_confirmation_mode')=='keypad':
                changes['keypad_prompt_approval_id']=state['approval_id'] if result.get('booking_status')=='awaiting_confirmation' else None
                changes['keypad_approval_id'],changes['keypad_armed_at']=None,None
            if call['status'] in TERMINAL:
                changes['last_response'] = ''
            if call['transcript_storage']:
                expires = (self.clock() + timedelta(days=min(cfg.transcript_retention_days,
                    self.store.tenant(principal.tenant_id)['retention_days']))).isoformat()
                for role, content in (('caller', text), ('assistant', result['response'])):
                    record = self.store.add('voice_transcripts', principal.tenant_id, {'conversation_id': call['conversation_id'],
                        'call_id': call_id, 'role': role, 'locale': call['voice_locale'], 'expires_at': expires})
                    self.gateway.secrets.put(principal.tenant_id, 'transcript:' + record['id'], content)
            # Full voice text is retained only in encrypted, expiry-bound transcript storage.
            for message in self.store.list('messages', principal.tenant_id, call['conversation_id']):
                self.store.update('messages', principal.tenant_id, message['id'], {'content': '', 'attachments': []})
            for event in self.store.list('provider_events', principal.tenant_id):
                if event.get('conversation_id') == call['conversation_id'] and isinstance(event.get('result'), dict):
                    safe = {key: value for key, value in event['result'].items() if key not in ('response', 'approval', 'outcome')}
                    self.store.update('provider_events', principal.tenant_id, event['id'], {'result': safe})
            call = self.store.update('call_sessions', principal.tenant_id, call_id, changes)
            self.store.add('provider_events', principal.tenant_id, {'call_id': call_id, 'fingerprint': sha256(text.encode()).hexdigest()}, external_key=key)
            self.record_event(principal, call, 'transcript')
            return call

    def arm_keypad(self, principal, call_id):
        """Private runtime hook: invoked only after full proposal playback survives its epoch."""
        with self.store.transaction():
            call=self.store.get('call_sessions',principal.tenant_id,call_id)
            if call['status'] in TERMINAL or call.get('booking_confirmation_mode')!='keypad':return False
            conversation=self.store.get('conversations',principal.tenant_id,call['conversation_id'])
            state=conversation.get('booking_state') or {}
            if state.get('status')!='awaiting_confirmation':return False
            if call.get('keypad_prompt_approval_id')!=state.get('approval_id'):return False
            approval=self.store.get('approvals',principal.tenant_id,state['approval_id'])
            if approval['status']!='pending' or datetime.fromisoformat(approval['expires_at'])<=self.clock():return False
            self.store.update('call_sessions',principal.tenant_id,call_id,{'keypad_approval_id':approval['id'],'keypad_armed_at':self.clock().isoformat()})
            return True

    @timed('voice_turn')
    def process_keypad(self, principal, call_id, item):
        """Trusted call-control input, not a transcript or model-provided authorization."""
        from .domain import KeypadInput
        item=KeypadInput.model_validate(item)
        principal=self.store.principal(principal.subject,principal.tenant_id);principal.require('execute')
        with self.store.transaction():
            call=self.store.get('call_sessions',principal.tenant_id,call_id)
            if call['status'] in TERMINAL or call.get('booking_confirmation_mode')!='keypad':raise DomainError('invalid_transition',409)
            key='voice-keypad:'+call_id+':'+item.utterance_id
            if self.store.find('provider_events',principal.tenant_id,key):return {**call,'duplicate':True}
            conversation=self.store.get('conversations',principal.tenant_id,call['conversation_id'])
            state=conversation.get('booking_state') or {}
            if state.get('status')!='awaiting_confirmation':return {**call,'ignored_utterance':True}
            approval=self.store.get('approvals',principal.tenant_id,state['approval_id'])
            if approval['status']!='pending' or datetime.fromisoformat(approval['expires_at'])<=self.clock():raise DomainError('expired',409)
            if item.digit=='1' and (call.get('keypad_approval_id')!=approval['id'] or not call.get('keypad_armed_at')
                    or item.received_at<datetime.fromisoformat(call['keypad_armed_at'])):
                return {**call,'ignored_utterance':True}
            if item.digit=='0':
                self.store.update('approvals',principal.tenant_id,approval['id'],{'status':'cancelled'})
                self.store.update('conversations',principal.tenant_id,conversation['id'],{'booking_state':{**state,'status':'cancelled'}})
                response=tr(call['voice_locale'],'booking_cancelled')
            else:
                assistant=self.store.get('assistants',principal.tenant_id,call['assistant_id'])
                self.store.update('approvals',principal.tenant_id,approval['id'],{'locale':call['voice_locale']})
                with self.providers.llm_session(assistant,conversation,principal,self.store,correlation_id.get() or uid()) as provider:
                    self.orchestrator.booking.executor.handoff(principal,assistant,conversation,'CreateAppointment',approval['arguments'],call['voice_locale'],approval['correlation_id'],provider=provider)
                    if hasattr(provider,'check_cancelled'):provider.check_cancelled()
                    result=self.orchestrator.approve(principal,approval['id'])
                    if hasattr(provider,'check_cancelled'):provider.check_cancelled()
                    response=result['response']
            call=self.store.update('call_sessions',principal.tenant_id,call_id,{'last_response':response,
                'keypad_approval_id':None,'keypad_armed_at':None,'last_activity_at':self.clock().isoformat()})
            for message in self.store.list('messages',principal.tenant_id,conversation['id']):
                self.store.update('messages',principal.tenant_id,message['id'],{'content':'','attachments':[]})
            self.store.add('provider_events',principal.tenant_id,{'call_id':call_id,'source':'trusted_keypad','approval_id':approval['id']},external_key=key)
            self.record_event(principal,call,'keypad_confirmed' if item.digit=='1' else 'keypad_rejected')
            return call

    def event(self, principal, call_id, action, *, locale=None, text='', destination='human', event_id=None,
              utterance_id=None, final=True, confirmed=False, tool=None, arguments=None):
        principal.require('execute')
        call = self.store.get('call_sessions', principal.tenant_id, call_id)
        event_id = event_id or uid()
        if action == 'transcript':
            if call['provider'] != 'mock':
                raise DomainError('forbidden', 403)
            return self.process_text(principal, call_id, text, utterance_id or event_id, final=final, tool=tool, arguments=arguments)
        key = 'call:' + call_id + ':' + event_id
        if self.store.find('provider_events', principal.tenant_id, key):
            return {**call, 'duplicate': True}
        next_state = TRANSITIONS.get(call['status'], {}).get(action)
        if not next_state:
            raise DomainError('invalid_transition', 409)
        if action == 'speak':
            self.speak(call, text)
        if action == 'transfer':
            cfg = self.config(principal.tenant_id, call['assistant_id'])
            target = cfg.human_escalation_number or ('human' if call['provider'] == 'mock' else '')
            if not target or destination not in ('human', target) or call['provider'] != 'mock' and not confirmed:
                raise DomainError('forbidden', 403)
            self.services(call)[0].transfer(call['provider_call_id'], target)
            return self.finish(principal, call_id, 'transferred')
        if action == 'terminate':
            self.services(call)[0].terminate(call['provider_call_id'])
            return self.finish(principal, call_id, 'ended')
        with self.store.transaction():
            changes = {'status': next_state, 'last_activity_at': self.clock().isoformat(),
                       'events': call['events'] + [{'event': action, 'at': self.clock().isoformat()}]}
            if action == 'language':
                self.services(call)[1].require(locale)
                changes.update(voice_locale=locale, locale_explicit=True, last_response=tr(locale, 'voice_language_switched'))
                self.store.update('conversations', principal.tenant_id, call['conversation_id'], {'active_locale': locale})
            call = self.store.update('call_sessions', principal.tenant_id, call_id, changes)
            self.store.add('provider_events', principal.tenant_id, {'call_id': call_id}, external_key=key)
            self.record_event(principal, call, action)
            return call

    def finish(self, principal, call_id, status='ended', error_code=None):
        with self.store.transaction():
            call = self.store.get('call_sessions', principal.tenant_id, call_id)
            if call['status'] in TERMINAL:
                return call
            conversation = self.store.get('conversations', principal.tenant_id, call['conversation_id'])
            state = conversation.get('booking_state')
            if state and state.get('status') == 'awaiting_confirmation':
                approval = self.store.get('approvals', principal.tenant_id, state['approval_id'])
                if approval['status'] == 'pending':
                    self.store.update('approvals', principal.tenant_id, approval['id'], {'status': 'cancelled'})
                    self.store.update('conversations', principal.tenant_id, conversation['id'],
                        {'booking_state': {**state, 'status': 'cancelled'}})
            if self.store.operations:
                self.store.operations.trace_voice(principal.tenant_id, 'session_closed', correlation_id.get(),
                    call_id=call_id, state=status)
            end = self.clock()
            duration = max(0, (end - datetime.fromisoformat(call['started_at'])).total_seconds())
            call = self.store.update('call_sessions', principal.tenant_id, call_id, {'status': status,
                'ended_at': end.isoformat(), 'duration_seconds': duration, 'error_code': error_code,
                'stream_active': False, 'last_response': ''})
            self.store.add('call_usage', principal.tenant_id, {'conversation_id': call['conversation_id'],
                'call_id': call_id, 'duration_seconds': duration, 'provider': call['provider'], 'price': None}, external_key=call_id)
            self.store.add('usage_records', principal.tenant_id, {'channel': 'voice', 'call_id': call_id,
                'duration_seconds': duration, 'provider': call['provider'], 'price': None})
            self.record_event(principal, call, status, error_code)
            if getattr(self,'ari_bridge',None): self.ari_bridge.close_for_call(principal.tenant_id,call_id)
            if status == 'transferred':
                self.store.add('call_participants', principal.tenant_id, {'conversation_id': call['conversation_id'],
                    'call_id': call_id, 'role': 'human', 'identifier': 'configured_human_destination'})
            return call

    def record_audio(self, principal, call, payload, encoding, rate, role='caller'):
        if not call['recording_enabled']: return
        import base64
        cfg = self.config(principal.tenant_id, call['assistant_id'])
        with self.store.transaction():
            record = self.store.add('voice_recordings', principal.tenant_id, {'conversation_id': call['conversation_id'],
                'call_id': call['id'], 'encoding': encoding, 'sample_rate': rate, 'role': role,
                'expires_at': (self.clock() + timedelta(days=min(cfg.transcript_retention_days,
                    self.store.tenant(principal.tenant_id)['retention_days']))).isoformat()})
            self.gateway.secrets.put(principal.tenant_id, 'recording:' + record['id'], base64.b64encode(payload).decode())

    def purge_expired(self, principal):
        principal.require('configure')
        count = 0
        with self.store.transaction():
            for table, prefix in (('voice_transcripts', 'transcript:'), ('voice_recordings', 'recording:')):
                for record in self.store.list(table, principal.tenant_id):
                    if record.get('redacted') or datetime.fromisoformat(record['expires_at']) > self.clock():
                        continue
                    secret = self.store.find('secrets', principal.tenant_id, prefix + record['id'])
                    if secret:
                        self.store.update('secrets', principal.tenant_id, secret['id'], {'encrypted': ''})
                    self.store.update(table, principal.tenant_id, record['id'], {'redacted': True})
                    count += 1
            self.store.audit(principal, 'voice:retention_redacted')
        return count

    def expire_idle_calls(self):
        """Internal lifecycle cleanup, including calls that never attach a media stream."""
        with self.store.lock:
            rows = self.store.db.execute('SELECT tenant_id,data FROM call_sessions').fetchall()
        count = 0
        for row in rows:
            call = json.loads(row['data'])
            if call['status'] in TERMINAL:
                continue
            cfg = self.config(row['tenant_id'], call['assistant_id'])
            if (self.clock() - datetime.fromisoformat(call['started_at'])).total_seconds() >= call.get('budget_seconds', cfg.call_timeout_seconds):
                actor = Principal(row['tenant_id'], call.get('owner_user_id', 'system'), 'admin', 'system-lifecycle')
                self.finish(actor, call['id'], 'failed', 'timeout')
                count += 1
        return count
