# Verified booking management

A management capability is signed per tenant with an encrypted server key and includes booking, revision, nonce and seven-day expiry. It is sent only through the verified booking email; public booking responses never return it. A typed name/email or public booking ID cannot authorize a change.

The link uses /widget/manage/PUBLIC_ID#token=…; fragment data is removed from visible browser history before requests and is not included in proxy URLs/logs. Management validates tenant/public integration, HMAC/expiry/revision and the Google event's private marker/status. Updates use current If-Match ETags and reject unexpected externally changed times. Rescheduling excludes only the exact proven owned event through minimal event listing; it never subtracts an assumed merged FreeBusy interval. Other event titles are neither requested nor returned.

Explicit confirmation is mandatory. Successful reschedule rotates revision/nonce, cancels old reminder/management jobs and creates updated jobs/link. Cancellation updates Google first, then the local appointment and pending jobs. Google sends cancellation notification; no redundant Gmail cancellation is queued. Same completed request can return its cached outcome with the prior valid signature; stale links cannot initiate a new mutation.

Expired/lost link recovery requires a fresh conversation-scoped email verification plus matching booking reference/email; only a new email is queued, never a returned capability. References are shown in receipts and management emails. If the integration is revoked/unpublished or proof is unavailable, contact the business; owner can manage its primary calendar directly. Google data/backups and separately retained business records are not erased by widget text-clear.

Live ownership/reschedule/cancel acceptance remains blocked on owner OAuth and explicitly approved tests. Offline contracts cover foreign tenant, tampering, expiration, revision rotation, updates/cancel and pending-job cancellation.
