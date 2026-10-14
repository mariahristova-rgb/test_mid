import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateSetupForm } from '../src/services/setupValidation.mjs';
test('invalid Save/Continue opens hidden FAQ and focuses first invalid field before any request', () => {
  const details = { tagName:'DETAILS', open:false, parentElement:null };
  const attributes = {};
  let focused=false, reported=false, notified=0;
  const control = { willValidate:true, validity:{valid:false}, parentElement:details,
    setAttribute:(key,value)=>attributes[key]=value, removeAttribute:key=>delete attributes[key], focus:()=>focused=true };
  const form = { querySelectorAll:()=>[control], checkValidity:()=>false, querySelector:()=>control, reportValidity:()=>reported=true };
  assert.equal(validateSetupForm(form,()=>notified++),false);
  assert.equal(attributes['aria-invalid'],'true');assert.equal(attributes['aria-describedby'],'setup-error');assert.equal(details.open,true);
  assert.equal(focused,true);assert.equal(reported,true);assert.equal(notified,1);
  control.validity.valid=true;form.checkValidity=()=>true;
  assert.equal(validateSetupForm(form,()=>notified++),true);
  assert.equal(attributes['aria-invalid'],undefined);assert.equal(notified,1);
});
test('Test Studio without a visible setup form preserves saved configuration path',()=>{
  assert.equal(validateSetupForm(null,()=>assert.fail()),true);
});
