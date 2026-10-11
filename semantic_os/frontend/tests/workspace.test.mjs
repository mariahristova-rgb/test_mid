import test from 'node:test';
import assert from 'node:assert/strict';
import { workspaceReads } from '../src/services/workspace.mjs';
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
test('every scenario and diagnostic trace label has localized evidence states', () => {
  for(const language of ['bg-BG','en-US']) {
    const labels=JSON.parse(readFileSync(new URL(`../src/locales/${language}.json`,import.meta.url)));
    for(const key of ['booking','short_confirmation','rejection','ambiguous','occupied','language_switch','handoff','interruption']) assert.ok(labels['scenario_'+key]);
    for(const key of ['PASS','FAIL','BLOCKED','notRecorded','notApplicable','MOCK_ONLY','voice_acceptance_blocked','aiPaused']) assert.ok(labels[key]);
  }
});
