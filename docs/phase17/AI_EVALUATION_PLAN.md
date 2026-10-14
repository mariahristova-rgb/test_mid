# Layered AI evaluation

Reviewed offline corpus: `semantic_os/config/phase17_evaluations.json`, version1.0.0. Run `.venv/Scripts/python.exe scripts/evaluate_phase17.py`; ignored redacted receipt: `artifacts/phase17/offline-evaluations.json`. Result on11October:15/15PASS. Receipt contains test IDs/categories/duration/hash, no raw failures/transcripts/credentials. Missing/skipped cases cannot pass.

Coverage reuses executable synthetic tests for BG/EN handoff, confirmation replay, injection containment, cross-tenant reads, language switching, Calendar DST/ownership, Gmail uncertainty, reminder scheduling, business/feature requests, reviewed quality promotion and widget trace erasure. This initial corpus is a selected regression layer, not exhaustive coverage of every requirement or a model benchmark.

Separate layers remain unverified: Qwen conversation simulations; approved-source public FAQ/unknown/confidential knowledge corpus; concurrent provider uncertainty; authorized public Google staging; attended browser/device; external pilot; human-heard voice. Add failures as reproducible synthetic tests before promoting behavior. Preserve existing `CustomerWorkspace` categorical signal/review workflow; accepting a suggestion does not mutate prompts, tools, policies or publication. Human review is mandatory.

Full unit suite remains the broader acceptance reference. Offline corpus never authorizes a live capability or pilot flag.
