# Presenter script — preparation, 8–12 minutes

**DEMO_BLOCKED. This is a planned script, not an accepted live demonstration.** First resolve safe speech consent and obtain listening/dashboard evidence. Fixed date: 13 October 2026, Europe/Sofia. Stop and version a new plan if the date expires.

1. 0–1 min: “This is a self-hosted AI Assistant supporting Bulgarian and English. SmileCare is fictional and the calendar is a demo calendar.”
2. 1–2 min: Open /dashboard and /assistants at http://127.0.0.1:3011. Show local Qwen3-4B, Receptionist and Task Execution Agent. “The receptionist talks to the customer; the execution agent performs authorized actions.”
3. 2–5 min, after the acceptance gate passes: authorized SIP client dials 2000. Expected configured greeting: “Hello! You have reached SmileCare. How can I help you?” Say exactly: “I would like to book an appointment for 2026-10-13 at 16:00.” Then “My name is Jane Example.” Verify the proposed name, fixed date, time and 30 minutes. Only then say “Yes, confirm.” Stop on a wrong or unclear proposal. This absolute spoken date format is planned, not rehearsed.
4. 5–7 min: Show the actual persisted booking ID, /appointments, /calls and selected call activity. Show both agents, CheckAvailability and CreateAppointment. Explain metadata-only voice history when transcript retention is disabled; never fabricate conversation text.
5. 7–10 min: Bulgarian scenario uses “Искам да запиша час за 13.10.2026 в 15:00.” Then “Казвам се Мария Демо.” and, only after a correct proposal, “Да.” The expected greeting is “Здравейте! Свързахте се със SmileCare. Как мога да Ви помогна?” Verify the dashboard language preference does not change the caller locale.
6. 10–12 min: “This demonstrates local SIP, not verified public-network telephony. The clinic calendar and notifications remain mocked. This is not production certification.” Show notification templates/isolated simulated output only as simulated; no real send is authorized.

Do not conceal measured long stage delays with a fabricated success message. If the script exceeds 12 minutes, safely stop the second call and disclose latency. The separate acceptance rehearsal needs three consecutive fully accepted calls; repeat Bulgarian at 17:00 for Иван Пример.

Fallback: explicitly labeled Web Chat using the same agents and fixed numeric date. Say “This is the Web Chat fallback; it is not a successful live voice call.” Existing Phase 8B recordings are historical recorded evidence, not new live events. Reset requires explicit -Confirm after stopping only this demo.
