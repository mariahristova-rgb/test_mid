# Local speech synthesis gate

No local TTS implementation or voice is configured. Existing synthetic/managed speech paths do not satisfy Phase 6C.

Piper's current upstream catalog includes `bg_BG-dimitar-medium` (22050 Hz). Its card lists CC0 data but fine-tuning from Lessac; the [Lessac source license](https://www.cstr.ed.ac.uk/projects/blizzard/2013/lessac_blizzard2013/license.html) excludes commercial use. This creates a licensing clarification gate, not an automatic finding that the derivative is cleared or prohibited. Review the exact approved artifact and the Piper engine license separately. English LJSpeech is another candidate, not an installed voice. No weights were downloaded.

eSpeak NG lists Bulgarian and English but is not installed/evaluated here. Neither candidate has passed an actual listening test. Required tests include the SmileCare greeting, Cyrillic names, dental terms, tomorrow's date, times and numbers. Preserve locale and reject unavailable Bulgarian speech; never silently use English. Record artifact hashes, license decision and listener acceptance before additional telephony activation.
