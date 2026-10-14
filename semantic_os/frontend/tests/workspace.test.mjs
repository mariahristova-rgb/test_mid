import test from 'node:test';
import assert from 'node:assert/strict';
import { workspaceReads, inboxToolNames, messageSpeaker } from '../src/services/workspace.mjs';
import { readFileSync } from 'node:fs';
test('configuration and summary routes avoid unrelated personal record collections', () => {
  for(const page of ['assistants','agents','dashboard','channels','integrations']) {
    assert.ok(!workspaceReads(page).includes('contacts'),page);
    assert.ok(!workspaceReads(page).includes('inbox'),page);
    assert.ok(!workspaceReads(page).includes('appointments'),page);
  }
  assert.ok(workspaceReads('inbox').includes('approvals'));
  assert.ok(workspaceReads('appointments').includes('appointments'));
});
test('Inbox action chooser only exposes allowed tools it can collect arguments for',()=>{
  const descriptors=['CheckAvailability','ConciergeBooking','SendMessage','UnknownTool'].map(name=>({name}));
  assert.deepEqual(inboxToolNames(descriptors,['CheckAvailability','ConciergeBooking','UnknownTool']),['CheckAvailability']);
  assert.deepEqual(inboxToolNames(descriptors,[]),[]);
});
test('human provenance is shown only for server-produced outbound messages',()=>{
  assert.equal(messageSpeaker({direction:'outbound',metadata:{kind:'human'}}),'human');
  assert.equal(messageSpeaker({direction:'inbound',metadata:{kind:'human'}}),'user');
  assert.equal(messageSpeaker({direction:'outbound'}),'assistant');
});
test('every scenario and diagnostic trace label has localized evidence states', () => {
  for(const language of ['bg-BG','en-US']) {
    const labels=JSON.parse(readFileSync(new URL(`../src/locales/${language}.json`,import.meta.url)));
    for(const key of ['reloadDiscardHelp','setupProgress','setupProgressHelp','faqOptionalEmpty','businessDetailsHelp','scheduleSetupHelp','serviceSetupHelp','escalationSetupHelp','previewSavedHelp','previewFaqConfig','previewBookingConfig','previewBehaviorConfig','previewRecoveryHelp','setupValidationHelp','preview_no_slot','simulatedPreview','previewCurrent','previewStale','setupActivated','setupTested','setupDraft']) assert.ok(labels[key]);
    for(const key of ['booking','short_confirmation','rejection','ambiguous','occupied','language_switch','handoff','interruption']) assert.ok(labels['scenario_'+key]);
    for(const key of ['PASS','FAIL','BLOCKED','notRecorded','notApplicable','MOCK_ONLY','voice_acceptance_blocked','aiPaused']) assert.ok(labels[key]);
  }
});
