# Install the website widget

Local app: http://127.0.0.1:3017. Widget origin: http://127.0.0.1:3020. Separate fictional site: http://127.0.0.1:3021. Public staging needs HTTPS and distinct origins; these loopback addresses are local demonstrations only.

1. Sign in, select your fictional business tenant, save and test its BG/EN Web Chat configuration, then activate it.
2. Open Website widgets. Save the exact authorized site origin, bilingual greetings/privacy notice, approved FAQ setting, optional booking, brand color and quotas.
3. Generate the ownership challenge. Serve its displayed nonce as text/plain at the displayed `.well-known/testmid-widget/…txt` path. Verification expires after one hour; redirects/private addresses are rejected outside explicit demo configuration.
4. Verify the origin, choose the activated saved draft and explicitly publish. Copy the generated script unchanged. Its ID is public; never add staff or model credentials.
5. Custom HTML: paste the script once before `</body>` or in a supported custom-code slot. WordPress: use an authorized custom HTML/header/footer integration. Shopify: use an authorized theme custom-code placement. These are CMS-neutral instructions, **not official plugins or verified CMS integrations**.
6. If the site uses CSP, authorize the dedicated widget origin for script-src, style-src, frame-src and connect-src as required. Review the actual site's policy; do not disable CSP globally. Do not proxy the iframe into the host origin.
7. Check script HTTP success, launcher, iframe load, successful bootstrap, an actual message and BG/EN switching. Test keyboard close/focus, screen reader status updates, narrow/mobile viewport and slow/offline retry. Successful snippet generation or HTTP 200 is insufficient installation proof.
8. Confirm a fictional appointment only after checking its details. Inspect its persisted result and conversation in the selected tenant's dashboard. The calendar and LLM are MOCK; browser voice is unavailable.

Use Unpublish for an immediate reversible stop, Rollback for a compatible prior snapshot, or Revoke for permanent public-ID retirement. Saving settings unpublishes and invalidates sessions. Clear removes chat text copies; separate business bookings remain. Review EMBED_SECURITY.md before public exposure.
