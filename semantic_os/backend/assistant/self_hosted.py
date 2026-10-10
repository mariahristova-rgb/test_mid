"""Explicit deployment-owned model/voice configuration; no downloads or caller URLs."""
import os
import json
from pathlib import Path
from .domain import DomainError
from .qwen import QwenSettings

def deployment_secret(name):
    path=os.getenv(name+'_FILE','')
    return Path(path).read_text().strip() if path else os.getenv(name,'')


def configure_environment(providers):
    mode = os.getenv('LLM_PROVIDER', 'mock')
    if mode == 'mock': return
    if mode not in ('local', 'qwen'): raise DomainError('unconfigured', 503)
    model = os.getenv('LLM_MODEL', 'qwen3-4b').casefold()
    models = {'qwen3-4b': 'Qwen3-4B', 'qwen3-8b': 'Qwen3-8B'}
    if model not in models: raise DomainError('invalid_input', 422)
    secret = deployment_secret('LLM_API_KEY')
    if not secret: raise DomainError('unconfigured', 503)
    settings = QwenSettings(endpoint=os.getenv('LLM_ENDPOINT', ''), model_name=models[model],
        served_model=os.getenv('LLM_SERVED_MODEL', models[model]),
        max_output_tokens=int(os.getenv('LLM_MAX_TOKENS', '256')),
        max_context_tokens=int(os.getenv('LLM_CONTEXT_LENGTH', '4096')),
        timeout_seconds=float(os.getenv('LLM_TIMEOUT', '20')),
        allow_private_http=os.getenv('LLM_ALLOW_PRIVATE_HTTP') == 'true',
        compact_intent=os.getenv('LLM_COMPACT_INTENT')=='true',compact_tools=os.getenv('LLM_COMPACT_TOOLS')=='true')
    providers.configure_qwen(settings, secret=secret)


def configure_speech(providers):
    if os.getenv('SELF_HOSTED_VOICE_ENABLED') != 'true': return
    if providers.qwen_settings is None: raise DomainError('unconfigured', 503)
    from .local_speech import FasterWhisperProvider, PiperProvider
    from .asterisk import AsteriskTelephonyProvider
    if os.getenv('STT_ENDPOINT') and os.getenv('TTS_ENDPOINT'):
        from .speech_http import LocalSpeechHTTP
        key=deployment_secret('SPEECH_API_KEY')
        providers.local_stt=LocalSpeechHTTP(os.environ['STT_ENDPOINT'],key,'faster_whisper',timeout=40)
        providers.local_tts=LocalSpeechHTTP(os.environ['TTS_ENDPOINT'],key,os.getenv('LOCAL_TTS_KIND','espeak_ng'),timeout=60)
        providers.asterisk=AsteriskTelephonyProvider()
        from .providers import LocalVoiceAdapter
        providers.channels['voice']=LocalVoiceAdapter()
        return
    path = os.getenv('LOCAL_SPEECH_CONFIG', '')
    if not path or not Path(path).is_absolute(): raise DomainError('unconfigured', 503)
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    stt = data['stt']
    providers.local_stt = FasterWhisperProvider(stt['root'], stt['manifest'], stt['sha256'],
        device=stt.get('device', 'cpu'), compute_type=stt.get('compute_type', 'int8'))
    providers.local_tts = PiperProvider(data['tts'])
    providers.asterisk = AsteriskTelephonyProvider()
    from .providers import LocalVoiceAdapter
    providers.channels['voice']=LocalVoiceAdapter()


def ari_settings():
    from .asterisk import ARISettings
    return ARISettings(endpoint=os.getenv('ARI_ENDPOINT', ''), username=os.getenv('ARI_USERNAME', ''), password=deployment_secret('ARI_PASSWORD'),
        tenant_id=os.getenv('ARI_TENANT_ID', ''), assistant_id=os.getenv('ARI_ASSISTANT_ID', ''), service_subject=os.getenv('ARI_SERVICE_SUBJECT', ''),
        advertised_host=os.getenv('VOICE_RTP_ADVERTISE_HOST', ''), asterisk_rtp_host=os.getenv('ASTERISK_RTP_HOST', ''),
        bind_host=os.getenv('VOICE_RTP_BIND_HOST', '0.0.0.0'))
