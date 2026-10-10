# Qwen artifact integration — deployment prerequisite

Current Phase 7D: read-only gs://ai_data_solutions/ontelyx/ai_model/Qwen3-4B/ was supplied and verified. All twelve cached artifacts match revision 1cfa9a7208912126459214e8b04321603b3df60c and passed SHA-256 verification. Original source/cache remains unchanged. scripts/provision_qwen_gcs.py uses the existing authenticated gcloud CLI for that exact prefix and pinned generations. Separate CPU conversion, model-volume staging and measurements are in docs/demo/MODEL_MEMORY_REPORT.md and LOCAL_MODEL_SETUP.md. The missing-source statements below describe the historical Phase 6C preflight.

## Historical Phase 6C prerequisite

The bucket, prefix and version are unknown. No cloud model has been fetched. Prefer the owner's existing authenticated endpoint when supplied.

`assistant/model_artifacts.py` implements a read-only ADC GCS source and pinned manifest/cache contract. `scripts/sync_qwen_artifacts.py --help` describes the required explicit arguments. Install the optional `semantic_os/backend/requirements-self-hosted.txt` dependencies in the deployment environment before using GCS. No credentials belong in arguments or source files.

Obtain a trusted local JSON manifest and its SHA-256 through the owner's trusted deployment channel. Required fields: `model_name` (`Qwen3-4B` default or explicitly selected `Qwen3-8B`), `version`, `format` (`gguf` or `hf_safetensors`), `license_spdx`, `license_reviewed`, and `files`. Each file declares relative `path`, exact SHA-256, `size_bytes`, and immutable GCS `generation`. A license file is mandatory. HF format additionally requires config and tokenizer files; executable/pickle artifacts are rejected. The review flag records an operator decision, not an automated license determination.

Use workload identity/ADC with bucket-scoped object-read permission and a prefix condition. The loader does not upload, delete or enumerate objects. Deployment-time synchronization verifies the pinned manifest and every file before publishing a versioned cache; verified caches are reused. Failed partial directories remain for operator inspection. Run one initializer per cache; concurrent initializer coordination is not implemented. Protect the cache against writes by other principals. Mount verified files read-only in inference containers; model weights are excluded from Git and image contexts.

Remaining verification: actual GCS IAM/access, artifact provenance/license, tokenizer identity, quantization, full runtime loading and resource fit. GGUF magic and declared model type checks are preliminary format checks, not a complete model validation.
