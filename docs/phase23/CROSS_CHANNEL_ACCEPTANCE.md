# Cross-channel gate

**BLOCKED.** Phase21CROSS_CHANNEL_IDENTITY_AND_CONSENT.md specifies proposed purpose-bound challenge/proof/offer/resume/revoke APIs and existing-JSON event design. It has not been approved/implemented/tested. The existing operator evidence contact link must never be interpreted as customer proof. No successful website↔voice/mobile/email continuation claimed.

After review: source verifies identity and explicitly offers minimal context; destination independently verifies same tenant/subject/session,purpose/expiry/nonce and accepts continuation. No raw history,callerID/string matching or pending approval copied. Recheck source revision/status,consent/revocation,availability and fresh consequential confirmation. Emails need separate recipient/send authorization.

Required fixtures: website→voice,voice→website,mobile↔voice,voice→email; wrong identity/tenant,expired/replayed proof,refusal/revoke/unlink,retention cleanup,concurrent sessions,changed booking,unknown writes and disconnect. Customer verification transport defaults unavailable in production; test injection cannot be selected by API data. No real sends,phone verification or independent customer database until approved architecture.
