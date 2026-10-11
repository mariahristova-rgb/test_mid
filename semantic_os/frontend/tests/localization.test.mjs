import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { parse as parseSFC } from '@vue/compiler-sfc';
import { parse as parseTemplate } from '@vue/compiler-dom';
const en = JSON.parse(readFileSync(new URL('../src/locales/en-US.json', import.meta.url), 'utf8'));
const bg = JSON.parse(readFileSync(new URL('../src/locales/bg-BG.json', import.meta.url), 'utf8'));
test('all interface resources have Bulgarian and English values', () => {
  assert.deepEqual(Object.keys(en).sort(), Object.keys(bg).sort());
  for (const [key, value] of Object.entries(bg)) { assert.ok(value.trim(), key); assert.ok(en[key].trim(), key); }
  for (const page of ['dashboard', 'assistants', 'agents', 'inbox', 'calls', 'channels', 'appointments', 'integrations', 'settings']) assert.match(bg[page], /[А-Яа-я]/u);
});
test('date formatting uses explicit Sofia timezone for both locales', () => {
  for (const locale of ['bg-BG', 'en-US']) {
    const parts = new Intl.DateTimeFormat(locale, { timeZone: 'Europe/Sofia', hour: '2-digit', minute: '2-digit', hour12: false }).formatToParts(new Date('2030-10-08T10:00:00Z'));
    assert.equal(parts.find(part => part.type === 'hour').value, '13');
  }
});
test('template contains no raw text nodes without localization', () => {
  for (const name of ['App.vue', 'views/WorkspaceView.vue', 'views/SaaSView.vue', 'components/MessagingConnections.vue', 'views/SetupView.vue', 'components/ConversationDebugger.vue','components/AssistantStudio.vue','views/WidgetView.vue','views/GoogleWorkspaceView.vue']) {
    const source = readFileSync(new URL('../src/' + name, import.meta.url), 'utf8');
    const ast = parseTemplate(parseSFC(source).descriptor.template.content);
    function visit(node) {
      if (node.type === 2) assert.doesNotMatch(node.content, /[\p{L}\p{N}]/u, name);
      for (const child of node.children || []) visit(child);
    }
    visit(ast);
  }
});
test('every literal UI translation key exists in both locales', () => {
  for (const name of ['App.vue', 'views/WorkspaceView.vue', 'views/SaaSView.vue', 'components/MessagingConnections.vue', 'views/SetupView.vue', 'components/ConversationDebugger.vue','components/AssistantStudio.vue','views/WidgetView.vue','views/GoogleWorkspaceView.vue']) {
    const source = readFileSync(new URL('../src/' + name, import.meta.url), 'utf8');
    for (const [, key] of source.matchAll(/\bt\(['"]([^'"]+)['"]\)/g)) {
      assert.ok(en[key] && bg[key], `${name}: ${key}`);
    }
  }
});
