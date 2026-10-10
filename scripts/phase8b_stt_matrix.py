"""Offline single-worker ablations on PCMU telephone fixtures; no expected-text prompt."""
import base64
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import wave
import sys
import resource
sys.path.insert(0, '/app')
import av
import numpy as np
from backend.assistant.audio import TurnBuffer, pcm_16khz, pcm_to_mulaw, mulaw_to_pcm
from backend.assistant.domain import AudioFrame
from backend.assistant.booking import pending_confirmation_decision
from backend.assistant.local_speech import FasterWhisperProvider


def convert(pcm, source_rate, target_rate):
    frame = av.AudioFrame.from_ndarray(np.frombuffer(pcm, dtype='<i2').reshape(1, -1), format='s16', layout='mono')
    frame.sample_rate = source_rate
    resampler = av.AudioResampler(format='s16', layout='mono', rate=target_rate)
    return b''.join(f.to_ndarray().tobytes() for f in [*resampler.resample(frame), *resampler.resample(None)])


def main():
    out = Path('/evidence')
    config = json.loads(Path(os.environ['STT_CONFIG']).read_text())
    engine = FasterWhisperProvider(config['root'], config['manifest'], config['sha256'],
        device='cpu', compute_type='int8', vad_filter=True, cpu_threads=4, chunk_seconds=8,
        vocabulary=config.get('vocabulary', {}), timeout=60)
    cases = json.loads((out/'voice-cases.json').read_text(encoding='utf-8'))
    report = {'timestamp': datetime.now(timezone.utc).isoformat(), 'single_worker': True,
        'device': 'cpu', 'compute_type': 'int8', 'source': 'authorized synthetic installed Windows Ivan',
        'new_models_downloaded': False, 'human_audio': False, 'results': []}
    for case in cases:
        source = out/'windows-voice'/('bg-BG-'+case['label']+'.wav')
        with wave.open(str(source)) as wav:
            rate = wav.getframerate(); pcm = wav.readframes(wav.getnframes())
            if wav.getnchannels()!=1 or wav.getsampwidth()!=2: raise RuntimeError('Unexpected PCM')
        telephone = mulaw_to_pcm(pcm_to_mulaw(convert(pcm, rate, 8000)))
        phone_file = out/'phone-fixtures'/source.name
        phone_file.parent.mkdir(exist_ok=True)
        with wave.open(str(phone_file), 'wb') as wav:
            wav.setparams((1,2,8000,0,'NONE','not compressed')); wav.writeframes(telephone + b'\0'*32000)
        buffer = TurnBuffer(silence_ms=1800, threshold=400, pre_roll_ms=200)
        finalized = []
        padded = telephone + b'\0'*32000
        active_ms = 0
        for number, offset in enumerate(range(0,len(padded),320)):
            frame = AudioFrame(sequence=number,utterance_id='fixture',encoding='pcm16',sample_rate=8000,
                payload=base64.b64encode(padded[offset:offset+320]).decode())
            item, active = buffer.feed(frame)
            if active: active_ms += len(padded[offset:offset+320])/16
            if item: finalized.append(item)
        for variant in ('baseline', 'bandlimited_padding', 'beam3_padding'):
            input_pcm = pcm_16khz(telephone,8000) if variant=='baseline' else convert(telephone,8000,16000)
            if variant!='baseline': input_pcm=b'\0'*8000+input_pcm+b'\0'*8000
            started = time.monotonic()
            options = dict(language='bg',beam_size=3 if variant=='beam3_padding' else 1,
                condition_on_previous_text=False,vad_filter=True,chunk_length=8,max_new_tokens=96)
            if 'bg-BG' in engine.vocabulary: options['initial_prompt']=engine.vocabulary['bg-BG']
            segments, info = engine.model.transcribe(np.frombuffer(input_pcm,dtype='<i2').astype(np.float32)/32768,**options)
            text=' '.join(segment.text for segment in segments).strip()
            row={'case':case['label'],'expected_text':case['text'],'variant':variant,'actual_text':text,
                'decision_if_pending':pending_confirmation_decision(text),'wall_ms':(time.monotonic()-started)*1000,
                'phone_sha256':hashlib.sha256(telephone).hexdigest(),'phone_audio_ms':len(telephone)/16,
                'vad_final_count':len(finalized),'vad_active_ms':active_ms,'endpoint_window_ms':1800,
                'min_speech_duration_ms':0,'language':'bg','beam_size':options['beam_size']}
            row['process_peak_rss_bytes'] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
            report['results'].append(row)
            (out/'stt-matrix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
            print(json.dumps(row,ensure_ascii=False),flush=True)


if __name__=='__main__': main()
