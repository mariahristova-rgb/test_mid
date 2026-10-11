# Concierge UX — Phase 14

The shared iframe now starts with **Welcome to Ontelyx**, product/demo scheduling context, Europe/Sofia and seven actions: booking, explore, information, business inquiry, reschedule, cancel and feature suggestion. Modified controls are localized in concierge-labels.js; approved product Q&A remains in the existing conversation runtime. Unknown questions get a grounded inquiry/demo offer, not invented integrations or proprietary knowledge.

Desktop uses the existing native navy/cyan/system-font design with a lazy iframe, clear request states and a date/slot/details/verified-email/consent workflow. Mobile ≤768 CSS px uses a full-height safe-area panel, dynamic visual-viewport height, background scroll locking/inert siblings, back/close restoration and a sticky composer inside the iframe. Cookiebot dialog events temporarily hide the floating launcher. These are implemented foundations, not verified real-device accessibility.

UI and conversation language are separate. BG/EN selection is explicit; only the existing optional remember-language choice writes device preference. Handoffs carry locale. Calendar times always use Europe/Sofia. Email proof, forms, action receipts, errors and management use localized text. Google invitation boilerplate follows Google's/recipient's own localization; our templates do not control it.

Technical retention/mock notices move into accessible privacy details. With Google disconnected, scheduling says temporarily unavailable and creates nothing. Browser voice remains hidden/unavailable; no mic permission is enabled. No claim that a mock calendar is live is made.

Sources: semantic_os/widget/{frame.html,frame.css,frame.js,concierge.js,concierge-labels.js,manage.html,manage.js}; website src/components/AiAssistantEntry.vue and AiAssistantView.vue. Only approved policy/receipt data crosses the shared v1 API; no Google/model/admin credentials enter presentation.
