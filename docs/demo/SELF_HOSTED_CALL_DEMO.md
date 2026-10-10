# SmileCare self-hosted demo — blocked

The synthetic SmileCare seed, two-dentist schedule, Qwen routing and SIP call demo are not implemented yet. No existing tenant was relabeled as a working self-hosted deployment.

Required inputs: exact existing Qwen3-4B GCS version or authenticated endpoint, target inference host, existing local STT artifacts and accepted Bulgarian/English TTS artifacts with licensing clarification. Then seed fictional data idempotently with Europe/Sofia timezone and explicit appointment durations/work hours.

Acceptance scenario: SIP 1001 calls extension 2000, hears “Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?”, requests a prophylactic examination, supplies date/name and confirms. Both agents use the shared Qwen endpoint; tools enforce authorization, confirmation and deduplication. Verify persisted booking and dashboard evidence, then repeat in English. Resolve tomorrow from the conversation timestamp in Europe/Sofia. This scenario has not been executed.
