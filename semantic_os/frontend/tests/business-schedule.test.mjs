import assert from 'node:assert/strict';
import test from 'node:test';
import {scheduleLocal,scheduleInstant} from '../src/services/businessSchedule.mjs';
test('business interval picker resolves tenant timezone independently of browser timezone',()=>{
  assert.equal(scheduleInstant('2030-10-09T15:00','Europe/Sofia'),'2030-10-09T12:00:00.000Z');
  assert.equal(scheduleLocal('2030-10-09T12:00:00Z','Europe/Sofia'),'2030-10-09T15:00');
  assert.equal(scheduleInstant('2030-10-09T23:00','Pacific/Honolulu'),'2030-10-10T09:00:00.000Z');
});
test('nonexistent,ambiguous and malformed local times do not silently select an instant',()=>{
  for(const value of ['2030-03-31T03:30','2030-10-27T03:30','2030-02-31T12:00',''])assert.throws(()=>scheduleInstant(value,'Europe/Sofia'));
  assert.equal(scheduleLocal('','Europe/Sofia'),'');
});
