"""Actual isolated neural CPU TTS evaluation; does not grant production readiness."""
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import torch
import torchaudio
import torchaudio.pipelines._wav2vec2.impl as wav_impl
from backend.assistant.bgtts_vendor.model import load_for_inference
from backend.assistant.bgtts_vendor.tokenizer import TTSTokenizer
from backend.assistant.bgtts_vendor.codec import CodecV6
from backend.assistant.bgtts_vendor.inference import generate
import soundfile as sf

def main():
    torch.set_num_threads(2); torch.set_num_interop_threads(1)
    # Replace the bundle's network/pickle default with explicit local weights-only loading.
    bundle=torchaudio.pipelines.WAVLM_BASE_PLUS
    original=wav_impl.Wav2Vec2Bundle.get_model
    def local_model(self,*,dl_kwargs=None):
        model=wav_impl.utils._get_model(self._model_type,self._params)
        state=torch.load('/models/torch-cache/hub/checkpoints/wavlm_base_plus.pth',map_location='cpu',weights_only=True)
        model.load_state_dict(state)
        if self._normalize_waveform: model=wav_impl.utils._extend_model(model,normalize_waveform=True)
        return model.eval()
    wav_impl.Wav2Vec2Bundle.get_model=local_model
    model=load_for_inference('/models/tts/checkpoint_inference.pt',device='cpu')
    codec=CodecV6(device='cpu',model_directory='/models/codec'); tokenizer=TTSTokenizer()
    reference=codec.encode('/models/tts/samples/sample_female_bg1.wav')['global_embedding']
    out=Path('/out'); out.mkdir(exist_ok=True)
    results=[]
    for locale,text,name in (('bg-BG','Здравейте! Свързахте се със СмайлКеър. Как мога да Ви помогна?','greeting'),
            ('bg-BG','Искам да запиша час за следващия понеделник в петнадесет часа.','request'),
            ('bg-BG','Казвам се Мария Демо.','name'),('bg-BG','Потвърждавам.','confirm'),
            ('en-US','Hello, I would like to book a dental checkup next Monday at three PM.','request')):
        start=time.monotonic(); torch.manual_seed(42)
        codes=generate(model,tokenizer,text,reference,temperature=.3,top_k=250,max_new_tokens=450,device='cpu')
        if codes is None: raise RuntimeError('Neural synthesis produced no audio tokens')
        audio=codec.decode(codes,reference).detach().cpu().numpy().reshape(-1)
        target=out/(locale+'-'+name+'.wav'); sf.write(str(target),audio,24000)
        item={'locale':locale,'phrase':name,'seconds':len(audio)/24000,'wall_ms':(time.monotonic()-start)*1000,
            'audio':target.name,'first_audio_ms':None,'intelligibility':'REQUIRES_REVIEW','timestamp':datetime.now(timezone.utc).isoformat()}
        results.append(item); print(json.dumps(item),flush=True)
    (out/'neural-tts-results.json').write_text(json.dumps(results,indent=2))

if __name__=='__main__': main()
