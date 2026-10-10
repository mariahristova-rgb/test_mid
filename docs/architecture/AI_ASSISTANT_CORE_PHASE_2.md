# Phase 2: functional assistant core

Scope: test_mid only. This increment completes the first natural-language Web Chat booking workflow using the existing cleaned Vue/FastAPI application. Calendar and LLM interpretation are synthetic mock providers; no production-readiness or live integration claim is made.

## Baseline inspected before editing

Reviewed the removal report/manifest, target architecture, orchestration/language/data-model docs, composition root, domain/configuration APIs, persistence, provider adapters, tool registry, frontend and existing tests. The branch was verified as `codex/phase1-repository-audit`; the copied repository remains untracked/unborn, so change sets are represented by files and documentation, not an historical Git diff.

Observed baseline: source syntax/excluded-import check passed; **46 backend tests passed**; frontend typecheck and build passed. There was no proprietary runtime-import or build blocker. Historical documents do not substitute for these fresh checks. The remaining functional gap was that ordinary chat only clarified booking requests, while booking relied on explicit structured UI tool selection.

## Implemented change set

| Files | Responsibility / change |
|---|---|
| `backend/assistant/domain.py` | Typed booking interpretation request/result, persisted booking-state DTO, CalendarProvider port and configurable default booking duration |
| `backend/assistant/booking.py` | Explicit ReceptionistAgent and TaskExecutionAgent; validated handoffs; availability/details/proposal/confirmation dialogue; original date reference and timezone snapshot |
| `backend/assistant/calendar.py` | Replaceable mock calendar with tenant-owned availability/booking/reschedule/cancel and transactional conflict checks |
| `backend/assistant/providers.py` | Deterministic mock natural-language intent/date/name/duration extraction through the LLM port; no vendor SDK |
| `backend/assistant/orchestration.py` | Common-channel integration, trusted receive clock, persisted pending dialogue, existing approval execution, locale switching and one reply per turn |
| `backend/assistant/tools.py` | Reused permission-controlled registry now delegates calendar operations to the calendar port; checks availability again before creation |
| `backend/assistant/api.py` | Config defaults exposed safely for old records; clock injection for synthetic tests; administrator-only tenant-scoped execution trace |
| `backend/assistant/language.py` | Localized booking dialogue; reliable bilingual vocabulary; relative dates/weekdays independent of reply language and explicit tenant timezone |
| `frontend/src/views/WorkspaceView.vue`, locale JSONs | Existing Web Chat UI now defaults to automatic language resolution, supports explicit switching, exposes booking duration and uses smaller conversation refreshes |
| `backend/tests/test_booking_workflow.py` | Natural-language acceptance, persistence/restart, midnight/timezone, duplicate/permission/consent/provider/trace tests |
| `scripts/demo_booking.py`, `scripts/browser_smoke.mjs` | Reproducible API artifact and actual bilingual browser demonstration |

No new package dependency, proprietary intelligence component, destructive migration, real calendar booking or live provider call was introduced. Existing identity/tenant enforcement, store, transaction boundary, schemas, approvals/idempotency, Vue controls, translated resources, history and feedback components were reused.

## Required demonstration

The saved [BOOKING_DEMO.json](BOOKING_DEMO.json) comes from actual API calls against separate in-memory mock calendars. Its fixed synthetic message timestamp is **2030-10-08 09:00 UTC**, with tenant timezone **Europe/Sofia**; tomorrow therefore resolves to **2030-10-09 15:00 +03:00**. Actual application messages use the server's trusted receive timestamp, not that fixed demonstration clock.

| Customer | Receptionist reply / executor action |
|---|---|
| `Здравейте, искам да запиша час за утре в 15:00.` | Detect bg-BG; persist timestamp/zone; validated receptionist→executor CheckAvailability handoff; mock calendar reports available; ask `Как се казвате?` and disclose configured 30-minute duration |
| `Казвам се Иван Иванов.` | Validate details; recheck availability; validated CreateAppointment proposal; persist immutable approval; show exact name/date/zone/duration and request confirmation; no booking yet |
| `Да, потвърждавам.` | Application verifies explicit affirmation and role/tool grants; executor executes CreateAppointment once; receptionist replies `Часът е потвърден за 09.10.2030 15:00 Europe/Sofia.` |
| `Hello, I would like to book an appointment for tomorrow at 15:00.` | Detect en-US; same tool/handoff/calendar path; ask `What is your name?` |
| `My name is John Smith.` | English proposal and confirmation request with the same timezone and duration |
| `Yes, confirm.` | One appointment; receptionist replies `Appointment confirmed for 10/09/2030 03:00 PM Europe/Sofia.` |

Default duration is an assistant setting, bounded to 5–480 minutes; a supported explicit duration overrides it and is shown before confirmation. Full interpretation is deliberately constrained: supported booking phrases, relative words/weekday+HH:MM, ISO/localized numeric timestamps, explicit name introductions or a plain name when requested, and bounded hour/minute durations. Missing/invalid/ambiguous times request clarification rather than guessed booking. This is not an unrestricted natural-language model.

## Safety and persistence

The first booking turn saves a typed `booking_state` inside the tenant-owned conversation, including reference timestamp, timezone, resolved start, duration/name, locale, stage and approval ID. Details arriving after tenant midnight reuse that original reference; database reopen does not reset the dialogue. State is additive JSON data in the existing schema; no table/data migration is necessary.

Read tools require actor permission plus assistant/executor allowlists and enabled/assigned agents. A provider can suggest an intent but cannot grant authorization: it cannot inject tenant IDs/tool keys into the strict interpretation schema, and its `confirm` classification cannot bypass the application-owned exact-affirmation gate. Booking still uses the existing confirmed approval execution path. Confirmation before required details does not book. Direct confirmation buttons remain supported.

Language detection initializes a conversation; ambiguous text preserves its locale. Explicit switching keeps neutral arguments and changes the dialogue/handoff/reply locale. Handoffs and completed tool records share approval correlation; trace phases distinguish proposal from execution. The final reply identifies the receptionist in message metadata. GET `/api/conversations/{id}/executions` is administrator-only and validates tenant/conversation ownership.

Provider events prevent same-event replay from running actions twice; completed approvals return the original outcome. A later repeated affirmative does not create another booking. Changed details cancel the old proposal, and decline cancels the pending request. Calendar availability is checked again in the creation transaction, so two customers cannot confirm the same slot. Approval expiry and revoked permissions are rechecked.

## Verification

Final command results are recorded in IMPLEMENTATION_STATUS. Acceptance includes the exact Bulgarian and English requests; midnight and non-UTC tenant-day calculation; role/tool revocation; stale/expired/replayed confirmations; unavailable and concurrently claimed slots; database reopen; provider-output injection and false confirmation; locale switching and administrator trace ownership. Retained backend, frontend, secret-scanner and browser tests are included, not replaced.

Observed results: **72 backend tests passed** (46 retained + 26 new), **7 frontend/security tests passed**, Vue typecheck/lint/build passed, source-boundary/syntax checks passed, and `pip check` reported no broken requirements. The headless browser completed both natural-language dialogues without selecting business tools, confirmed both appointments through chat, checked history/call controls, localized browser title and mobile overflow. The final staged Git-visible source/config/docs Gitleaks scan checked 84 files with no leaks; ignored real credentials/data were excluded and scanner networking was disabled. No production provider was configured or exercised.

Run the artifact demonstration from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/demo_booking.py --output docs/architecture/BOOKING_DEMO.json
.\.venv\Scripts\python.exe -m unittest discover -s semantic_os/backend/tests -q
```

On Windows, sandboxed asyncio socketpairs may require the permitted local test execution mode. TestClient's existing httpx deprecation notice does not fail the tests. The demo writes UTF-8 directly to preserve Cyrillic.

## Remaining integrations

The Web Chat application flow works against mocked LLM/calendar infrastructure. Live LLM interpretation, external calendar/availability policy, network outbox/idempotency, hard provider timeouts, streaming, real Voice/STT/TTS, mailbox ingestion, official WhatsApp and SMS integrations remain unconfigured. Single-process SQLite, current retention scope and deployment controls retain the limitations documented in TARGET_ARCHITECTURE and IMPLEMENTATION_STATUS. No production readiness is asserted.
