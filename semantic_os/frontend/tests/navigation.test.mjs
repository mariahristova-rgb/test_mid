import test from 'node:test';
import assert from 'node:assert/strict';
import {navigationGroups,permittedGroups} from '../src/services/navigation.mjs';
test('existing routes appear once and remain reachable in three experiences',()=>{
  const pages=navigationGroups.flatMap(g=>g.pages);
  assert.equal(new Set(pages).size,pages.length);
  for(const page of ['inbox','appointments','google','testing','calls','administration']) assert.ok(pages.includes(page));
});
test('viewer navigation does not expose operator or configuration tasks',()=>{
  assert.deepEqual(permittedGroups('viewer').flatMap(g=>g.pages),['dashboard','assistants','inbox','appointments','leads','analytics','health']);
  assert.deepEqual(permittedGroups(undefined),[]);
});
test('operator and admin navigation preserve role distinctions',()=>{
  const operator=permittedGroups('operator').flatMap(g=>g.pages);
  assert.ok(operator.includes('testing'));assert.ok(!operator.includes('google'));
  assert.ok(!permittedGroups('admin').flatMap(g=>g.pages).includes('administration'));
  assert.ok(permittedGroups('admin',true).flatMap(g=>g.pages).includes('administration'));
});
