"""Bounded audio codecs/buffering. No SIP implementation or provider SDK."""
import base64
import math
import struct
from .domain import DomainError


def decode_payload(value):
    try:
        result = base64.b64decode(value, validate=True)
    except (ValueError, TypeError):
        raise DomainError('invalid_input', 422) from None
    if len(result) > 32000:
        raise DomainError('invalid_input', 413)
    return result


def mulaw_to_pcm(data):
    samples = []
    for code in data:
        code = ~code & 255
        value = (((code & 15) << 3) + 132) << ((code >> 4) & 7)
        value -= 132
        samples.append(-value if code & 128 else value)
    return struct.pack('<' + 'h' * len(samples), *samples)


def pcm_to_mulaw(data):
    if len(data) % 2:
        raise DomainError('invalid_input', 422)
    output = bytearray()
    for sample, in struct.iter_unpack('<h', data):
        sign = 128 if sample < 0 else 0
        value = min(32635, abs(sample)) + 132
        exponent = max(0, min(7, value.bit_length() - 8))
        mantissa = (value >> (exponent + 3)) & 15
        output.append(~(sign | exponent << 4 | mantissa) & 255)
    return bytes(output)


def pcm_16khz(data, source_rate):
    if len(data) % 2:
        raise DomainError('invalid_input', 422)
    if source_rate == 16000:
        return data
    # Simple sample duplication preserves telephony bandwidth; a production
    # speech adapter may replace this with a tested resampler.
    return b''.join(data[i:i + 2] * 2 for i in range(0, len(data), 2))


def energy(data):
    if not data or len(data) % 2:
        return 0.0
    values = [value for value, in struct.iter_unpack('<h', data)]
    return math.sqrt(sum(value * value for value in values) / len(values))


class TurnBuffer:
    def __init__(self, *, max_seconds=20, silence_ms=600, threshold=400, pre_roll_ms=200):
        if not 0<=pre_roll_ms<=500: raise ValueError('Bounded audio pre-roll required')
        self.max_bytes = max_seconds * 32000
        self.max_seconds = max_seconds
        self.silence_limit = silence_ms
        self.threshold = threshold
        self.buffer = bytearray()
        self.silence = 0
        self.speech = False
        self.last_sequence = -1
        self.utterance_id = None
        self.encoding = None
        self.rate = None
        self.pre_roll_ms=pre_roll_ms
        self.pre_roll=bytearray()

    def feed(self, frame):
        if frame.sequence <= self.last_sequence:
            return None, False
        raw = decode_payload(frame.payload)
        if self.buffer and (self.encoding != frame.encoding or self.rate != frame.sample_rate or self.utterance_id != frame.utterance_id):
            raise DomainError('invalid_input', 422)
        self.last_sequence = frame.sequence
        if (self.encoding,self.rate,self.utterance_id)!=(frame.encoding,frame.sample_rate,frame.utterance_id):
            self.pre_roll.clear()
        self.encoding, self.rate, self.utterance_id = frame.encoding, frame.sample_rate, frame.utterance_id
        pcm = mulaw_to_pcm(raw) if frame.encoding == 'mulaw' else raw
        active = bool(raw) if frame.encoding == 'fixture_utf8' else energy(pcm) >= self.threshold
        if active:
            if not self.speech and frame.encoding!='fixture_utf8':
                self.buffer.extend(self.pre_roll)
                self.pre_roll.clear()
            self.speech, self.silence = True, 0
        elif self.speech and frame.encoding != 'fixture_utf8':
            self.silence += int(len(pcm) / (2 * frame.sample_rate) * 1000)
        if self.speech or frame.encoding == 'fixture_utf8':
            self.buffer.extend(pcm)
        else:
            self.pre_roll.extend(pcm)
            capacity=frame.sample_rate*2*self.pre_roll_ms//1000
            if capacity: del self.pre_roll[:-capacity]
            else: self.pre_roll.clear()
        limit = 10000 if frame.encoding == 'fixture_utf8' else self.max_seconds * frame.sample_rate * 2
        if len(self.buffer) > limit:
            self.reset()
            raise DomainError('limit_reached', 413)
        done = frame.final or self.speech and self.silence >= self.silence_limit
        if not done:
            return None, active
        result = (bytes(self.buffer), frame.encoding, frame.sample_rate, frame.utterance_id)
        self.reset()
        return result, active

    def reset(self):
        self.buffer.clear()
        self.pre_roll.clear()
        self.silence, self.speech, self.utterance_id = 0, False, None
