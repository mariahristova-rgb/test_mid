import test from 'node:test';
import assert from 'node:assert/strict';
import {safeMetric} from '../src/services/localPerformance.mjs';
test('local metrics retain only numeric core vitals, never attribution or private text',()=>{
  assert.deepEqual(safeMetric({name:'LCP',value:123,attribution:{url:'private.example',content:'private'},entries:[{text:'private'}]}),{name:'LCP',value:123});
  for(const input of [{name:'URL',value:1},{name:'CLS',value:NaN},{name:'INP',value:-1},{name:'LCP',value:Infinity}]) assert.equal(safeMetric(input),null);
});
