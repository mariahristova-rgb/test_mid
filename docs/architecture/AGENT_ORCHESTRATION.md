# Agent orchestration and tools

Receptionist and executor are tenant-owned configurable agents. Both support bg-BG/en-US. `booking.py` now implements the natural-language booking dialogue through a typed LLM interpretation port and replaceable mock calendar. The deterministic mock extracts supported booking/time/name/duration suggestions; the application validates them and retains tool/consent authority. Structured UI tools remain supported. Live LLM interpretation is unconfigured. See [the core Phase 2 report](AI_ASSISTANT_CORE_PHASE_2.md) and [saved API demonstration](BOOKING_DEMO.json).

Assistant-owned bilingual FAQ entries answer explicitly configured questions. Appointment/cancellation/reschedule requests receive localized clarification. Configured escalation keywords prepare a validated human-request handoff/approval; approval creates the human task and pauses further tool automation by default. An authorized operator can explicitly resume the conversation. Older queued approvals also respect the pause policy.

Handoff fields: tenant, conversation, source/target agent, intent/tool key, validated arguments, locale, correlation ID, maximum steps/depth/tool calls. Initial path is receptionist→executor with one tool call. Budget/depth violations and different-tenant/wrong-agent handoffs fail. There is no recursive handoff mechanism. AgentExecution persists the handoff and ToolExecution persists the completed outcome, validated arguments, approver and correlation.

| Tool | Input contract | Confirmation |
|---|---|---|
| CheckAvailability | Aware start datetime, bounded duration | Read only; no confirmation |
| CreateAppointment | Aware start, duration, contact name | Explicit approval |
| RescheduleAppointment | Same plus tenant-owned appointment ID | Explicit approval |
| CancelAppointment | Tenant-owned appointment ID | Explicit approval |
| SendMessage | Enabled channel, recipient, bounded Unicode content | Explicit approval; opt-out/window checks apply |
| CreateFollowUpTask | Title, aware due datetime | Explicit approval |
| EscalateToHuman | Bounded reason | Explicit approval, persisted human task |

Tool registry publishes input/output JSON schemas, timeout and confirmation policy. Each execution checks actor role, assistant tool allowlist, executor allowlist and enabled state. Approval execution rechecks policy and assistant/channel status, validates arguments again, verifies the persisted argument fingerprint and expiry, and rejects client-supplied arguments. The confirmation endpoint requires `confirmed:true`. Approval IDs are tenant-bound and 15 minutes valid. Repeated completed confirmations return the original result without a second write or dispatch.

Natural chat can explicitly affirm an already presented, complete booking proposal with supported Bulgarian/English confirmation phrases. This application-owned consent check is separate from LLM intent, so a false model classification cannot authorize creation. Executor checks availability, gathers missing details through the receptionist, proposes validated arguments and only executes after consent. Persisted booking state anchors relative dates to the original message timestamp and tenant zone across follow-ups/restart. Old proposals are cancelled when details change. The receptionist formats the final localized outcome; one response is dispatched per customer turn.

Appointment overlap checks use aware datetimes, durations and tenant scope under a serialized write transaction. Rescheduling excludes the current appointment and updates its reminder. Cancelling does not delete the record. Outcomes preserve locale and render dates in explicit tenant time zone. Consequential writes are synthetic/mock application actions, not external booking-system operations.

Failures return localized safe codes. Authenticated rejected requests are audited without bodies/prompts/credentials. Completed tool execution is transactionally audited. Attempts that fail before a principal is known cannot have tenant audit ownership and return a safe error. The mock tool elapsed-time limit is 5 seconds checked before commit; it is not a cancellable timeout for a hung live SDK. Live providers require hard timeouts/cancellation and outbox-backed retry semantics before installation.

Reminder jobs are created by approved appointments and persist locale-independent resource references and due timestamps. Explicit `/api/jobs/run` claims due jobs under the repository transaction, dispatches localized mock reminders, and records completion or bounded retry (three attempts). Opt-out/disabled errors terminate retry. No live or silently scheduled external sends occur.
