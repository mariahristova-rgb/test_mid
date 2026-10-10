"""Content-free structured spans and bounded tenant-scoped operational aggregates."""
from collections import defaultdict, deque
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
import logging
from threading import RLock
from time import monotonic

correlation_id = ContextVar('assistant_correlation_id', default='')


class Operations:
    def __init__(self):
        self.lock = RLock()
        self.metrics = defaultdict(lambda: {'count': 0, 'errors': 0, 'total_ms': 0, 'max_ms': 0})
        self.worker = {'status': 'disabled', 'last_tick_at': None, 'last_error': None, 'inflight': 0}
        self.gauges = defaultdict(dict)
        self.voice_traces = {}

    def trace_voice(self, tenant, stage, correlation, **fields):
        """Bounded diagnostic metadata; no transcript, audio, name or model arguments."""
        stages = {'audio_received', 'vad_final', 'stt_partial', 'stt_final', 'locale_selected',
                  'pending_state', 'confirmation_evaluated', 'agent_authorized', 'tool_completed',
                  'appointment_persisted', 'tts_completed', 'output_packet_sent', 'session_closed'}
        allowed = {'call_id', 'conversation_id', 'utterance_id', 'locale', 'state', 'decision',
                   'sample_rate', 'audio_ms', 'duration_ms', 'partial_supported', 'transcript_present',
                   'provider_intent', 'intent_source', 'approval_id', 'appointment_id', 'parent_correlation_id'}
        if stage not in stages or set(fields) - allowed:
            raise ValueError('Content-free voice trace fields required')
        with self.lock:
            if tenant not in self.voice_traces:
                if len(self.voice_traces) >= 2000: return
                self.voice_traces[tenant] = deque(maxlen=256)
            self.voice_traces[tenant].append({'stage': stage, 'correlation_id': correlation,
                                             'monotonic_ms': round(monotonic()*1000, 3), **fields})

    def gauge(self, tenant, kind, value):
        with self.lock:
            if tenant not in self.gauges and len(self.gauges) >= 2000: return
            self.gauges[tenant][kind] = value

    def observe(self, kind, tenant='', *, duration_ms=0, error=None):
        with self.lock:
            key = (tenant, kind)
            if key not in self.metrics and len(self.metrics) >= 2000: key = ('', 'overflow')
            row = self.metrics[key]
            row['count'] += 1
            row['errors'] += int(error is not None)
            row['total_ms'] += duration_ms
            row['max_ms'] = max(row['max_ms'], duration_ms)
        if error:
            logging.getLogger('assistant.operations').warning(json.dumps({'event': kind, 'code': error,
                'correlation_id': correlation_id.get(), 'duration_ms': round(duration_ms, 2)}))

    @contextmanager
    def span(self, kind, tenant=''):
        start, error = monotonic(), None
        try: yield
        except BaseException as exc:
            error = getattr(exc, 'code', 'operation_failed')
            raise
        finally: self.observe(kind, tenant, duration_ms=(monotonic() - start) * 1000, error=error)

    def snapshot(self, tenant):
        with self.lock:
            return {'metrics': {kind: {**row, 'mean_ms': row['total_ms'] / row['count']} for (owner, kind), row in self.metrics.items() if owner == tenant},
                'worker': dict(self.worker), 'gauges': dict(self.gauges.get(tenant, {})),
                'voice_trace': list(self.voice_traces.get(tenant, ()))}


def timed(kind):
    def decorate(function):
        @wraps(function)
        def wrapped(self, *args, **kwargs):
            store = getattr(self, 'store', None)
            ops = getattr(store, 'operations', None)
            tenant = (args[0].get('tenant_id', '') if isinstance(args[0], dict) else getattr(args[0], 'tenant_id', '')) if args else ''
            if not ops: return function(self, *args, **kwargs)
            with ops.span(kind, tenant): return function(self, *args, **kwargs)
        return wrapped
    return decorate
