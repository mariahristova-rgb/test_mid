# Cloud staging and model measurement gate
No cloud resources, model download, GPU runtime, DNS change or deadline extension performed. No spending incurred by this increment. Cloud Run API/GPU Qwen3-8B, PostgreSQL/Cloud SQL and tenant-isolated Cloud Storage are not deployed or measured.

Proposed architecture requires reviewed infrastructure-as-code, private database/object access, pinned model/tokenizer/config and quantization, bounded concurrency/pooling, durable idempotency/jobs, least-privilege service accounts, Secret Manager references, redacted logging and lifecycle policies. These are requirements, not implemented deployment evidence.

Capacity model without fabricated measurements: for N tenants and 50 conversations/day, daily turns = N × 50 × measured turns/conversation; daily input/output tokens = daily turns × measured tokens/turn × measured agent-call multiplier. Evaluate N=10/25/50/100 using actual pilot distributions, peak concentration and tooling overhead. Cost requires current region/SKU prices and measured GPU busy/idle seconds; numeric estimates not yet established.

Acceptance requires actual p50/p95 prefill/generation/queue, warm/cold start, throughput, error rate, memory, fairness and cost under authorized load. No real GPU result or production capacity claim.
