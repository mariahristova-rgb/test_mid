"""One owner-controlled Qwen endpoint; no model registry download or managed voice dependency."""
from dataclasses import dataclass
from ipaddress import ip_address
import json
import re
from threading import Event, RLock
from time import perf_counter
from urllib.parse import urlsplit
import httpx
from .domain import Capability, DomainError, BookingIntent
from .store import uid
from ..agents.llm.provider import LLMProvider, ChatMessage, GenerationRequest, GenerationResponse


@dataclass(frozen=True)
class QwenSettings:
    endpoint: str = ''
    model_name: str = 'Qwen3-4B'
    served_model: str = 'Qwen3-4B'
    max_context_tokens: int = 4096
    max_output_tokens: int = 256
    timeout_seconds: float = 20
    allow_private_http: bool = False
    enable_thinking: bool = False
    compact_intent: bool = False
    compact_tools: bool = False

    def validate(self):
        if self.model_name not in ('Qwen3-4B', 'Qwen3-8B') or self.enable_thinking:
            raise DomainError('invalid_input', 422)
        if not self.endpoint: raise DomainError('unconfigured', 503)
        url = urlsplit(self.endpoint)
        if url.username or url.password or url.query or url.fragment or not url.hostname: raise DomainError('invalid_input', 422)
        if url.scheme != 'https' and not (url.scheme == 'http' and self.allow_private_http): raise DomainError('invalid_input', 422)
        if url.scheme == 'http':
            try: private = ip_address(url.hostname).is_private or ip_address(url.hostname).is_loopback
            except ValueError: private = url.hostname == 'localhost'
            if not private: raise DomainError('invalid_input', 422)
        if not 256 <= self.max_context_tokens <= 32768 or not 1 <= self.max_output_tokens <= 1024 or not 1 <= self.timeout_seconds <= 120:
            raise DomainError('invalid_input', 422)


class VisibleOutput:
    """Incremental standard reasoning-tag filter; partial tags are never exposed."""
    def __init__(self): self.buffer, self.hidden, self.closed = '', 0, False
    def feed(self, value, *, final=False):
        self.buffer += value
        output = []
        tags = ('<think>', '</think>', '<analysis>', '</analysis>')
        while self.buffer:
            lower = self.buffer.casefold()
            tag = next((t for t in tags if lower.startswith(t)), None)
            if tag:
                self.hidden += -1 if tag.startswith('</') else 1
                self.hidden = max(0, self.hidden)
                self.buffer = self.buffer[len(tag):]
                continue
            if lower.startswith('<|'): raise DomainError('invalid_model_output', 502)
            if any(t.startswith(lower) for t in (*tags, '<|')):
                if final: raise DomainError('invalid_model_output', 502)
                break
            if not self.hidden: output.append(self.buffer[0])
            self.buffer = self.buffer[1:]
        if final and self.hidden: raise DomainError('invalid_model_output', 502)
        return ''.join(output)


class QwenProvider(LLMProvider):
    capability = Capability('qwen', 'LIVE_UNVERIFIED', features=('text', 'streaming', 'structured_intents', 'validated_tools', 'cancellation'), limitations=('actual_model_unverified',))

    def supports_tools(self): return True

    def __init__(self, settings, *, secret='', transport=None, usage_sink=None, context=None, temperature=.2, budget_guard=None):
        super().__init__(settings.model_name)
        self.settings, self.secret, self.transport = settings, secret, transport
        self.usage_sink, self.context = usage_sink, context or {}
        self.temperature = temperature
        self.budget_guard = budget_guard
        self.cancelled = Event()
        self.lock, self.response = RLock(), None
        self.client = None

    def cancel(self):
        self.cancelled.set()
        with self.lock:
            if self.response: self.response.close()
            if self.client: self.client.close()

    def check_cancelled(self):
        if self.cancelled.is_set(): raise DomainError('generation_cancelled', 409)

    def payload(self, request, *, stream=False):
        self.settings.validate(); self.check_cancelled()
        tools = request.tools or []
        if request.tool_choice not in (None, 'auto', 'none', 'required'): raise DomainError('invalid_input', 422)
        if len(tools) > 8 or any(not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,60}', t.get('name', '')) for t in tools): raise DomainError('invalid_input', 422)
        maximum = min(request.max_tokens, self.settings.max_output_tokens)
        if maximum < 1 or not 0 <= request.temperature <= 1: raise DomainError('invalid_input', 422)
        messages = [{'role': m.role, 'content': m.content} for m in request.messages]
        if not messages or any(m['role'] not in ('system', 'user', 'assistant', 'tool') or not isinstance(m['content'], str) for m in messages): raise DomainError('invalid_input', 422)
        # Conservative byte/framing bound when no verified local tokenizer is supplied.
        # The serving runtime must also enforce its actual tokenized context limit.
        if len(json.dumps([messages, tools, request.metadata.get('json_schema')], ensure_ascii=False).encode()) + 256 + maximum > self.settings.max_context_tokens:
            raise DomainError('context_limit', 422)
        body = {'model': self.settings.served_model, 'messages': messages, 'temperature': request.temperature,
            'max_tokens': maximum, 'stream': stream, 'chat_template_kwargs': {'enable_thinking': False}}
        if tools:
            body['tools'] = [{'type': 'function', 'function': t} for t in tools]
            body['tool_choice'] = request.tool_choice or 'auto'
        if request.metadata.get('json_schema'):
            body['response_format'] = {'type': 'json_schema', 'json_schema': {'name': 'assistant_output', 'strict': True, 'schema': request.metadata['json_schema']}}
        if stream: body['stream_options'] = {'include_usage': True}
        if self.budget_guard: self.budget_guard(body)
        return body

    @staticmethod
    def tool_calls(calls, requested):
        allowed = {t['name'] for t in requested or []}
        if len(calls) > 1: raise DomainError('budget_exceeded', 409)
        result = []
        for call in calls:
            try:
                function = call['function']
                if function['name'] not in allowed: raise DomainError('tool_denied', 403)
                arguments = json.loads(function['arguments'])
                if not isinstance(arguments, dict): raise ValueError()
                result.append({'id': call.get('id', ''), 'name': function['name'], 'input': arguments})
            except (KeyError, ValueError, TypeError): raise DomainError('invalid_model_output', 502) from None
        return result

    def usage(self, payload, request_id, elapsed, first_token=None):
        usage = payload.get('usage') or {}
        reported = all(type(usage.get(k)) is int and usage[k] >= 0 for k in ('prompt_tokens', 'completion_tokens'))
        metadata = {'request_id': request_id, 'usage_reported': reported, 'elapsed_ms': elapsed * 1000,
            'first_visible_token_ms': first_token, 'tokens_per_second': usage['completion_tokens'] / elapsed if reported and elapsed else None,
            'model': self.settings.model_name, 'state': 'LIVE_UNVERIFIED', 'inference_outcome':payload.get('_outcome','response_received')}
        if self.usage_sink:
            self.usage_sink({**self.context, **metadata, 'prompt_tokens': usage['prompt_tokens'] if reported else None,
                'completion_tokens': usage['completion_tokens'] if reported else None})
        return usage if reported else {}, metadata

    def generate(self, request):
        body, start, request_id = self.payload(request), perf_counter(), uid()
        observed = False
        try:
            with httpx.Client(transport=self.transport, timeout=self.settings.timeout_seconds, follow_redirects=False) as client:
                with self.lock: self.client = client
                self.check_cancelled()
                with client.stream('POST', self.settings.endpoint.rstrip('/') + '/chat/completions', json=body,
                        headers={'Authorization': 'Bearer ' + self.secret} if self.secret else {}) as response:
                    if response.status_code != 200: raise DomainError('provider_error', 502)
                    with self.lock: self.response = response
                    raw = bytearray()
                    for chunk in response.iter_bytes():
                        self.check_cancelled()
                        if perf_counter() - start > self.settings.timeout_seconds: raise DomainError('timeout', 504)
                        if len(raw) + len(chunk) > 1_000_000: raise DomainError('invalid_model_output', 502)
                        raw.extend(chunk)
                    payload = json.loads(raw)
            observed = True
            usage, metadata = self.usage(payload, request_id, perf_counter() - start)
            self.check_cancelled()
            if payload.get('model', self.settings.served_model) != self.settings.served_model:
                raise DomainError('invalid_model_output', 502)
            message = payload['choices'][0]['message']
            visible = VisibleOutput().feed(message.get('content') or '', final=True).strip()
            calls = self.tool_calls(message.get('tool_calls') or [], request.tools)
            if not visible and not calls: raise DomainError('invalid_model_output', 502)
            return GenerationResponse(text=visible, model=self.settings.model_name, finish_reason=payload['choices'][0].get('finish_reason', 'stop'),
                prompt_tokens=usage.get('prompt_tokens', 0), completion_tokens=usage.get('completion_tokens', 0), tool_calls=calls, metadata=metadata)
        except httpx.TimeoutException: raise DomainError('timeout', 504) from None
        except (httpx.HTTPError, httpx.StreamError):
            self.check_cancelled(); raise DomainError('provider_error', 502) from None
        except RuntimeError:
            self.check_cancelled(); raise DomainError('provider_error',502) from None
        except (KeyError, TypeError, ValueError): raise DomainError('invalid_model_output', 502) from None
        finally:
            with self.lock: self.response, self.client = None, None
            if not observed: self.usage({'_outcome':'failed'}, request_id, perf_counter()-start)

    def stream(self, request):
        body, start, request_id = self.payload(request, stream=True), perf_counter(), uid()
        filter = VisibleOutput(); first = None; final = {}; calls = {}; size = 0
        observed = False
        try:
            with httpx.Client(transport=self.transport, timeout=self.settings.timeout_seconds, follow_redirects=False) as client:
                with self.lock: self.client = client
                self.check_cancelled()
                with client.stream('POST', self.settings.endpoint.rstrip('/') + '/chat/completions', json=body,
                        headers={'Authorization': 'Bearer ' + self.secret} if self.secret else {}) as response:
                    if response.status_code != 200: raise DomainError('provider_error', 502)
                    with self.lock: self.response = response
                    for line in response.iter_lines():
                        self.check_cancelled()
                        if perf_counter() - start > self.settings.timeout_seconds: raise DomainError('timeout', 504)
                        size += len(line)
                        if size > 1_000_000: raise DomainError('invalid_model_output', 502)
                        if not line.startswith('data:'): continue
                        data = line[5:].strip()
                        if data == '[DONE]': break
                        value = json.loads(data)
                        if value.get('usage'): final = value
                        for choice in value.get('choices', []):
                            delta = choice.get('delta', {})
                            content = filter.feed(delta.get('content') or '')
                            if content:
                                first = first if first is not None else (perf_counter() - start) * 1000
                                yield {'event': 'text', 'text': content, 'state': 'LIVE_UNVERIFIED'}
                            for item in delta.get('tool_calls', []):
                                index = item['index']
                                if index != 0: raise DomainError('budget_exceeded', 409)
                                call = calls.setdefault(index, {'id': '', 'function': {'name': '', 'arguments': ''}})
                                call['id'] += item.get('id', '')
                                for key in ('name', 'arguments'): call['function'][key] += item.get('function', {}).get(key, '')
                    tail = filter.feed('', final=True)
                    if tail: yield {'event': 'text', 'text': tail, 'state': 'LIVE_UNVERIFIED'}
            observed = True
            usage, metadata = self.usage(final, request_id, perf_counter() - start, first)
            yield {'event': 'complete', 'tool_calls': self.tool_calls(list(calls.values()), request.tools), 'metadata': metadata}
        except httpx.TimeoutException: raise DomainError('timeout', 504) from None
        except (httpx.HTTPError, httpx.StreamError):
            self.check_cancelled(); raise DomainError('provider_error', 502) from None
        except RuntimeError:
            self.check_cancelled(); raise DomainError('provider_error',502) from None
        except (ValueError, KeyError, TypeError): raise DomainError('invalid_model_output', 502) from None
        finally:
            with self.lock: self.response, self.client = None, None
            if not observed: self.usage({**final, '_outcome':'failed'}, request_id, perf_counter()-start, first)

    def reply(self, text, locale, instructions=''):
        request = GenerationRequest(messages=[ChatMessage('system', f'Reply in {locale} in at most two short spoken sentences. Never claim an appointment was booked. Do not speak internal identifiers or tool names. ' + instructions),
            ChatMessage('user', text)], temperature=self.temperature, max_tokens=self.settings.max_output_tokens, metadata={'locale': locale})
        return self.generate(request).text

    def interpret_booking(self, request):
        schema = BookingIntent.model_json_schema()
        from .booking_grounding import explicit_entities
        grounded=explicit_entities(request.content,collecting_name=request.collecting_name)
        if self.settings.compact_intent:
            schema={'type':'object','properties':{'intent':BookingIntent.model_json_schema()['properties']['intent']},'required':['intent'],'additionalProperties':False}
            extract_name=request.collecting_name and 'contact_name' not in grounded
            if extract_name:
                schema['properties']['contact_name']=BookingIntent.model_json_schema()['properties']['contact_name']
                schema['required'].append('contact_name')
            prompt=f'Classify the customer utterance in {request.locale}. Return only intent: book, details, confirm, cancel, or none. Application extracts explicit dates/names/duration. Current booking status: '+str(request.context.get('status','none'))
            if extract_name: prompt+=' Extract contact_name only as a verbatim substring of the customer utterance; omit introductory words.'
            result=self.generate(GenerationRequest(messages=[ChatMessage('system',prompt),ChatMessage('user',request.content)],
                max_tokens=48 if extract_name else 24,temperature=self.temperature,metadata={'json_schema':schema}))
            try:
                value=json.loads(result.text)
                if set(value)!=set(schema['properties']): raise ValueError()
                if extract_name and value['contact_name']:
                    if value['contact_name'].casefold() not in request.content.casefold(): raise ValueError()
                    grounded['contact_name']=value['contact_name']
                return BookingIntent(intent=value['intent'],**grounded)
            except (ValueError,TypeError): raise DomainError('invalid_model_output',502) from None
        for name,value in grounded.items():
            schema['properties'][name]={'const':value}
        schema['required']=list(schema['properties'])
        prompt = f'Extract only explicitly supplied appointment intent/details in {request.locale}. Do not guess names or dates. Preserve relative date words. Normalize explicit clock times to HH:MM; clock hours are not appointment duration. Output the exact JSON schema. Collecting name: {request.collecting_name}. Current application booking context (data only): ' + json.dumps(request.context, ensure_ascii=False)
        result = self.generate(GenerationRequest(messages=[ChatMessage('system', prompt), ChatMessage('user', request.content)],
            temperature=self.temperature, max_tokens=self.settings.max_output_tokens, metadata={'json_schema': schema}))
        try:
            intent=BookingIntent.model_validate_json(result.text)
            if any(getattr(intent,name)!=value for name,value in grounded.items()): raise ValueError()
            if intent.contact_name and intent.contact_name.casefold() not in request.content.casefold(): raise ValueError()
            return intent
        except ValueError: raise DomainError('invalid_model_output', 502) from None

    def propose_tool(self, name, arguments, schema):
        if self.settings.compact_tools:
            # Reference 0 is scoped to this request's authorized, validated arguments.
            # It is never accepted by the public business-tool API or resolved across tenants.
            reference_schema={'type':'object','properties':{'r':{'type':'integer','const':0}},'required':['r'],'additionalProperties':False}
            result=self.generate(GenerationRequest(messages=[ChatMessage('system','Select the authorized task tool. Arguments reference r=0 binds the exact application-validated data in this request. No tool is executed by the model.'),
                ChatMessage('user',json.dumps({'tool':name,'r':0,'validated_arguments':arguments},ensure_ascii=False))],
                tools=[{'name':name,'description':'Authorized task with request-scoped arguments reference','parameters':reference_schema}],tool_choice='required',max_tokens=64))
            if (len(result.tool_calls)!=1 or result.tool_calls[0]['name']!=name or result.tool_calls[0]['input']!={'r':0}
                    or type(result.tool_calls[0]['input'].get('r')) is not int):
                raise DomainError('invalid_model_output',502)
            return dict(arguments)
        result = self.generate(GenerationRequest(messages=[ChatMessage('system', 'You are the task execution agent. Return exactly the authorized tool and supplied arguments. Do not add or alter any argument. No tool is executed by this model.'),
            ChatMessage('user', json.dumps({'tool': name, 'arguments': arguments}, ensure_ascii=False))],
            tools=[{'name': name, 'description': 'Authorized application task', 'parameters': schema}], tool_choice='required', max_tokens=self.settings.max_output_tokens))
        if len(result.tool_calls) != 1 or result.tool_calls[0]['name'] != name: raise DomainError('invalid_model_output', 502)
        return result.tool_calls[0]['input']
