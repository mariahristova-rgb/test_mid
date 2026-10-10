"""Replay existing synthetic phone WAVs through the actual VAD without model inference."""
import base64
import json
from pathlib import Path
import struct
import sys
import wave
import argparse
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.audio import TurnBuffer,pcm_to_mulaw
from semantic_os.backend.assistant.domain import AudioFrame

ROOT=Path(__file__).resolve().parents[1]


def main(silence=600,tag='audio-baseline'):
    out=ROOT/'artifacts/phase8'/tag; out.mkdir(parents=True,exist_ok=True)
    results=[]
    for source in sorted((ROOT/'artifacts/neural-voice-audio/call-input').glob('*.wav')):
        with wave.open(str(source)) as wav:
            if wav.getframerate()!=8000 or wav.getnchannels()!=1 or wav.getsampwidth()!=2:
                raise RuntimeError('Expected actual 8k mono PCM16 caller fixtures')
            pcm=wav.readframes(wav.getnframes())
        samples=struct.unpack('<'+'h'*(len(pcm)//2),pcm)
        onset=next((index/8 for index,value in enumerate(samples) if abs(value)>=40),None)
        payload=pcm_to_mulaw(pcm); buffer=TurnBuffer(silence_ms=silence); finals=[]; first_active=None
        for index in range(0,len(payload),160):
            frame=payload[index:index+160].ljust(160,b'\xff')
            item,active=buffer.feed(AudioFrame(sequence=index//160,utterance_id=source.stem,
                payload=base64.b64encode(frame).decode(),encoding='mulaw',sample_rate=8000))
            if active and first_active is None: first_active=index/8
            if item:
                finals.append({'final_at_ms':(index+160)/8,'pcm_bytes':len(item[0]),'retained_start_ms':(index+160)/8-len(item[0])/16})
                target=out/(source.stem+f'-vad-{len(finals)}.wav')
                with wave.open(str(target),'wb') as wav:
                    wav.setnchannels(1); wav.setsampwidth(2); wav.setframerate(8000); wav.writeframes(item[0])
        results.append({'source':source.name,'source_seconds':len(payload)/8000,'nonquiet_onset_ms':onset,
            'first_active_frame_ms':first_active,'speech_prefix_dropped_ms':None if onset is None or not finals else max(0,finals[0]['retained_start_ms']-onset),
            'finals':finals,'synthetic_only':True})
    (out/'vad-replay.json').write_text(json.dumps(results,indent=2))
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--silence-ms',type=int,default=600)
    parser.add_argument('--tag',default='audio-baseline')
    args=parser.parse_args(); main(args.silence_ms,args.tag)
