# Email integration

Implemented: signed provider-independent connector ingestion, MIME decoding, subject extraction, text/HTML handling, encrypted quarantined attachments, thread correlation, localized responses/signatures, persistent drafts, approval, scheduled follow-ups and delivery error handling. The outbound EmailProvider port has mock and gated TLS SMTP implementations. No IMAP poller, OAuth mailbox connection or provider-specific inbound service is installed.

Normalize sender and recipient mailboxes, reject header controls, validate configured recipient and require a trusted sender-validation attestation. MIME body instructions remain untrusted customer text; they cannot grant tools or bypass confirmation. Only plain text enters the agents. HTML scripts/styles/embedded objects are removed during extraction; outbound HTML escapes all text. UI interpolates text instead of rendering provider HTML.

`Message-ID`, `In-Reply-To` and References map a reply to an existing connection-scoped conversation only when the validated sender matches. New/unrecognized threads create new conversations. Thread locale is preserved; explicit language switching uses the shared resolver. Outbound SMTP supplies stable Message-ID, In-Reply-To, localized subject/body/signature and text + escaped HTML alternatives.

Default `email_draft_required=true` holds AI replies and scheduled mail for operator review. `POST /api/messages/{id}/approve-draft` requires explicit confirmation and the approve role. Authenticated operator replies during takeover are already authorized. No draft approval means no delivery job is dispatched.

For SMTP configure provider `smtp`, sender_id, public_origin, smtp_host, smtp_port (465 TLS or 587 STARTTLS), smtp_username, encrypted smtp_password and webhook_secret. The inbound signed connector remains separate from SMTP sending. Enable both live flags only after account/network policy review. Network errors are uncertain and not automatically resent. SMTP acceptance is `sent`, not proof of recipient delivery/read; no DSN parser is installed.

Attachment support is ingestion/storage/metadata only: at most 10 items and 2 MB per item, approved MIME types/magic, safe names, encrypted bytes, retention expiry and quarantine. No automatic downloads, scanner release, outbound attachment send or malware certification is claimed. OAuth token rotation, inbound mail identity infrastructure, bounce handling, mailbox OAuth consent and real bilingual account tests remain production gates.
