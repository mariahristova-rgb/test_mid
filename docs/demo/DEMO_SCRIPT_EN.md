# English demonstration — procedure, not a completed live test

1. Verify actual SIP 1001 registration and availability, then dial 2000. Start in English explicitly or verify automatic locale detection after the initial Bulgarian greeting.
2. Say: “Hello, I would like to book a dental checkup next Monday at 3 PM.” Next Monday is resolved from the actual conversation timestamp in Europe/Sofia, never a fixture date.
3. Supply a fictional name: “My name is Jane Smith.” Wait for the date/time/name/duration summary. Verify the proposed details before saying “Yes, confirm.” If the recognized name/date differs, correct it and wait for a new summary. There must be no appointment before explicit confirmation.
4. Verify spoken confirmation only after persistence. Open Appointments and Call activity; compare the actual booking identifier, tool execution and status.
5. Test occupied availability using an actual occupied calendar slot. Verify suggested slots and that no conflicting appointment was created.
6. Test language switching, interruption, provider failure and hangup separately. Verify stopped obsolete audio, terminal CallSession status and cleanup.

Use a new available slot for each journey. Two dentists can accept two simultaneous checkups, after which that slot is occupied. Complete and record three consecutive real booking journeys before marking the demo ready. The deterministic Web Chat fallback must be labeled MOCK when explicitly selected.
