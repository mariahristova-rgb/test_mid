"""Redacted configuration check; inference only with the explicit --probe-qwen option."""
import argparse
import json
import os
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from semantic_os.backend.assistant.providers import ProviderRegistry
from semantic_os.backend.assistant.self_hosted import configure_environment
from semantic_os.backend.assistant.qwen import QwenProvider
from semantic_os.backend.assistant.domain import DomainError, BookingInterpretationRequest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-qwen', action='store_true')
    args = parser.parse_args()
    keys = ('LLM_ENDPOINT','LLM_API_KEY','LOCAL_SPEECH_CONFIG','ARI_ENDPOINT','ARI_USERNAME','ARI_PASSWORD','VOICE_RTP_ADVERTISE_HOST','ASTERISK_RTP_HOST')
    report = {'configuration': {key: bool(os.getenv(key)) for key in keys}, 'live_call_count':0,
        'voice_validation':'NOT_RUN', 'model_probe':'NOT_RUN'}
    if args.probe_qwen:
        try:
            registry = ProviderRegistry()
            configure_environment(registry)
            if not registry.qwen_settings: raise DomainError('unconfigured', 503)
            receipts = []
            provider = QwenProvider(registry.qwen_settings, secret=registry.qwen_secret, usage_sink=receipts.append)
            probes = []
            for locale, text in (('bg-BG','Здравейте, искам да запиша час за утре в 15:00.'),
                    ('en-US','Hello, I would like to book an appointment tomorrow at 15:00.')):
                intent = provider.interpret_booking(BookingInterpretationRequest(content=text, locale=locale))
                probes.append({'locale':locale, 'intent':intent.intent, 'valid_booking_intent':intent.intent=='book'})
            arguments = {'starts_at':'2030-10-14T15:00:00+03:00', 'duration_minutes':30}
            from semantic_os.backend.assistant.tools import SCHEMAS
            proposed = provider.propose_tool('CheckAvailability', arguments, SCHEMAS['CheckAvailability'].model_json_schema())
            report.update(model_probe='PASSED' if all(p['valid_booking_intent'] for p in probes) and proposed==arguments else 'FAILED', probes=probes,
                tool_arguments_match=proposed==arguments, inference_measurements=receipts)
        except DomainError as exc: report.update(model_probe='BLOCKED', error_code=exc.code)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['model_probe'] in ('PASSED','NOT_RUN') else 1


if __name__ == '__main__': raise SystemExit(main())
