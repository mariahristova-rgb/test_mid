# Configuration and action mapping

ConnectionInput accepts only known providers/actions and fixture-prefixed resources. No base URL, access token, redirect or client-secret field. Unsupported action or foreign resource fails server-side. UI action chooser uses the backend descriptor and only saved action permissions appear on the connection card.

Calendar codecs require aware start/end with positive range. Management requires selected synthetic event ID plus etag. HubSpot mapping permits four explicit contact properties and synthetic email only. These previews validate codecs, not real appointment ownership or business working-hours availability. Existing application booking rules are not weakened or replaced.

Preview result is tied to connection revision and idempotency fingerprint. Editable provider selection does not change already saved connections. Old owner Google client/policy controls remain independent. Real calendar/resource selection, field-map editor and a customer activation request are still future live-contract work.
