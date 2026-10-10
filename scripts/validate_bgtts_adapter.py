"""Exercise the deployed adapter offline, including decoder-only warm operation."""
from datetime import datetime, timezone
import json
from pathlib import Path
import time
import wave
import io
from backend.assistant.neural_voice import BG38Voice


def main():
    started = time.monotonic()
    engine = BG38Voice('/models')
    preload_ms = (time.monotonic() - started) * 1000
    results = []
    out = Path('/out')
    for locale, name, text in (
        ('bg-BG', 'request', 'Здравейте, искам да запиша час за следващия понеделник в петнадесет часа.'),
        ('bg-BG', 'name', 'Казвам се Мария Демо.'),
        ('bg-BG', 'confirm', 'Да, потвърждавам часа за прегледа.'),
        ('en-US', 'request', 'Hello, I would like to book a dental checkup next Monday at three PM.'),
        ('en-US', 'name', 'My name is Jane Demo.'),
        ('en-US', 'confirm', 'Yes, I confirm the appointment.'),
    ):
        started = time.monotonic()
        audio = engine.wav(text, locale, engine.voice_ids[locale])
        elapsed = (time.monotonic() - started) * 1000
        with wave.open(io.BytesIO(audio)) as wav:
            seconds = wav.getnframes() / wav.getframerate()
        (out / f'{locale}-{name}.wav').write_bytes(audio)
        item = dict(locale=locale, phrase=name, input_text=text, seconds=seconds,
                    wall_ms=elapsed, first_audio_ms=None, intelligibility='REQUIRES_REVIEW')
        results.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    report = dict(timestamp=datetime.now(timezone.utc).isoformat(), preload_ms=preload_ms,
                  source='BG38_NEURAL_CPU_ADAPTER', results=results, human_validation='NOT_RUN')
    (out / 'adapter-results.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
