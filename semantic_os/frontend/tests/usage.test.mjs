import assert from 'node:assert/strict';
import test from 'node:test';
import {measuredQuantity} from '../src/services/usage.mjs';
test('usage quantities above Number precision retain every digit',()=>{
  const text='9007199254740993';
  for(const locale of ['bg-BG','en-US'])assert.equal(measuredQuantity(text,'token',locale).replace(/\D/g,''),text);
});
test('millisecond durations display exact locale seconds and reject invalid input',()=>{
  assert.equal(measuredQuantity('1234','millisecond','en-US'),'1.234');
  assert.equal(measuredQuantity('1234','millisecond','bg-BG'),'1,234');
  assert.equal(measuredQuantity('1000','millisecond','en-US'),'1');
  for(const input of ['NaN','-1','1.5','<script>'])assert.equal(measuredQuantity(input,'token','en-US'),null);
});
