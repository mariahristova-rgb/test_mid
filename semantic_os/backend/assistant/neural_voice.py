"""Reviewed small BG/EN neural voice. CPU-only, local weights, synthetic generic reference."""
import gc
import io
from pathlib import Path
from threading import BoundedSemaphore
from time import monotonic
import wave
from .domain import Capability,DomainError
from .audio import pcm_to_mulaw
from .local_speech import resample_pcm
from .espeak import spoken_text


class BG38Voice:
    capability=Capability('bgtts38','LIVE_UNVERIFIED',features=('local_neural_cpu',),limitations=('voice_acceptance_required',))
    voice_ids={'bg-BG':'bgtts-bg','en-US':'bgtts-en'}
    def __init__(self, root='/models'):
        from .speech_integrity import verify_bgtts_cache
        verify_bgtts_cache(root)
        import torch
        import torchaudio.pipelines._wav2vec2.impl as wav_impl
        from .bgtts_vendor.model import load_for_inference
        from .bgtts_vendor.codec import CodecV6
        from .bgtts_vendor.tokenizer import TTSTokenizer
        self.torch=torch; torch.set_num_threads(2); torch.set_num_interop_threads(1)
        def local_model(bundle,*,dl_kwargs=None):
            model=wav_impl.utils._get_model(bundle._model_type,bundle._params)
            state=torch.load(root+'/torch-cache/hub/checkpoints/wavlm_base_plus.pth',map_location='cpu',weights_only=True)
            model.load_state_dict(state)
            if bundle._normalize_waveform: model=wav_impl.utils._extend_model(model,normalize_waveform=True)
            return model.eval()
        wav_impl.Wav2Vec2Bundle.get_model=local_model
        self.model=load_for_inference(root+'/tts/checkpoint_inference.pt',device='cpu')
        self.codec=CodecV6(device='cpu',model_directory=root+'/codec')
        self.reference=self.codec.encode(root+'/tts/samples/sample_female_bg1.wav')['global_embedding']
        self.tokenizer=TTSTokenizer(); self.slot=BoundedSemaphore(1)
        # Encoding/reference extraction is completed once; only the wave decoder is needed per turn.
        extractor=self.codec.model.ssl_feature_extractor
        class DecoderGeometry(torch.nn.Module):
            """Keep exact convolution geometry used by decode, without encoder weights."""
            def __init__(self, source):
                super().__init__()
                self.ssl_sample_rate=source.ssl_sample_rate
                self.conv_config=tuple(source.conv_config)
            def get_minimum_input_length(self, length):
                for kernel,stride in reversed(self.conv_config):
                    length=(length-1)*stride+kernel
                return length
        self.codec.model.ssl_feature_extractor=DecoderGeometry(extractor)
        self.codec.model.local_encoder=None
        self.codec.model.global_encoder=None
        del extractor
        gc.collect()

    def wav(self,text,locale,voice):
        if locale not in self.voice_ids or voice!=self.voice_ids[locale]: raise DomainError('unsupported_locale',422)
        if not 0<len(text)<=1000: raise DomainError('invalid_input',422)
        if not self.slot.acquire(timeout=30): raise DomainError('timeout',504)
        from .bgtts_vendor.inference import generate,_split_text
        import numpy as np
        import soundfile as sf
        try:
            output=[]
            for chunk in _split_text(spoken_text(text,locale),self.tokenizer,self.model.config.max_text_len):
                self.torch.manual_seed(42)
                codes=generate(self.model,self.tokenizer,chunk,self.reference,temperature=.3,top_k=250,max_new_tokens=450,device='cpu')
                if codes is None: raise DomainError('provider_error',502)
                output.append(self.codec.decode(codes,self.reference).detach().cpu().numpy().reshape(-1))
            audio=np.concatenate(output)
            if len(audio)>60*24000: raise DomainError('limit_reached',413)
            buffer=io.BytesIO(); sf.write(buffer,audio,24000,format='WAV',subtype='PCM_16')
            return buffer.getvalue()
        finally:self.slot.release()

    def synthesize(self,text,locale,voice=None):
        import numpy as np
        import soundfile as sf
        import torchaudio.functional as audio
        samples,rate=sf.read(io.BytesIO(self.wav(text,locale,voice)),dtype='float32')
        # Bandlimit before telephone downsampling; point sampling aliases high-frequency speech.
        narrow=audio.resample(self.torch.from_numpy(samples),rate,8000).numpy()
        pcm=np.clip(np.rint(narrow*32768),-32768,32767).astype('<i2').tobytes()
        return pcm_to_mulaw(pcm)
