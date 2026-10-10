# Local transcription prerequisite

faster-whisper is listed as an optional dependency; it is not installed or integrated. No local STT artifact or actual microphone/RTP transcription is verified.

The implementation must receive an explicit existing local CTranslate2 model path with `local_files_only=True`. A registry model-name shortcut must not trigger an unapproved weight download. Configure Bulgarian/English explicitly per session, process finalized VAD chunks outside the audio loop and bound workers, input duration and cancellation. Measure real Bulgarian dental terms, dates and caller names on the target hardware before acceptance.
