import test from 'node:test';
import assert from 'node:assert/strict';
import {languageSaver,reconciledLocale} from '../src/services/profile-language.mjs';
test('profile preference applies at login unless the user switched while loading',()=>{
  assert.equal(reconciledLocale({ui_locale:'bg-BG'},'en-US',false),'bg-BG');
  assert.equal(reconciledLocale({ui_locale:'bg-BG'},'en-US',true),'en-US');
  assert.equal(reconciledLocale({ui_locale:'invalid'},'en-US',false),'en-US');
});
test('locale writes are ordered and failure can retry',async()=>{
  const writes=[],reports=[];let release;const pending=new Promise(resolve=>{release=resolve;});
  const save=languageSaver(async locale=>{writes.push(locale);if(writes.length===1)await pending;if(writes.length===2)throw Error('offline');},()=>true,code=>reports.push(code));
  const a=save('tenant','bg-BG'),b=save('tenant','en-US');await Promise.resolve();assert.deepEqual(writes,['bg-BG']);release();await Promise.all([a,b]);
  assert.deepEqual(writes,['bg-BG','en-US']);assert.equal(reports.at(-1),'localeSyncFailed');await save('tenant','en-US');assert.equal(reports.at(-1),null);
});
test('queued writes for the previous tenant are discarded',async()=>{
  let current='first',release;const pending=new Promise(resolve=>{release=resolve;});const writes=[];
  const save=languageSaver(async locale=>{writes.push(locale);await pending;},context=>context===current,()=>{});
  const a=save('first','bg-BG'),b=save('first','en-US');await Promise.resolve();current='second';release();await Promise.all([a,b]);assert.deepEqual(writes,['bg-BG']);
});
