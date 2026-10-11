import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { gzipSync } from 'node:zlib';
import test from 'node:test';
const read = name => readFileSync(new URL('../../widget/' + name, import.meta.url), 'utf8');
test('versioned loader stays within the 4 KiB compressed budget', () => {
  assert.ok(gzipSync(read('v1.js')).length <= 4096);
  assert.doesNotMatch(read('v1.js'), /innerHTML|document\.write|localStorage/);
});
test('widget text resources cover both mandatory languages and declared labels', () => {
  const source=read('catalog.js');
  const labels=Function(source.replace('export const labels', 'const labels')+';return labels')();
  assert.deepEqual(Object.keys(labels['bg-BG']).sort(),Object.keys(labels['en-US']).sort());
  for(const [,key] of read('frame.html').matchAll(/data-label="([^"]+)"/g)) assert.ok(labels['bg-BG'][key] && labels['en-US'][key],key);
});
test('source contracts keep visitor credentials inside iframe and voice unavailable', () => {
  assert.doesNotMatch(read('v1.js'), /session_token|Authorization|microphone 'self'/);
  assert.match(read('frame.js'), /credentials: 'omit'/);
  assert.doesNotMatch(read('frame.js'), /innerHTML|insertAdjacentHTML|getUserMedia/);
  assert.match(read('v1.js'), /event\.source !== frame\.contentWindow/);
  assert.match(read('frame.js'), /event\.source !== window\.parent/);
});
