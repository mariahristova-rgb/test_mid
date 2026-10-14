import { test } from 'node:test';
import assert from 'node:assert/strict';
import { validateSetupForm } from '../src/services/setupValidation.mjs';
test('invalid Save/Continue opens hidden FAQ and focuses first invalid field before any request', async () => {
  const details = { tagName:'DETAILS', open:false, parentElement:null };
  const attributes = {'aria-describedby':'field-help'};
  let focused=false, reported=false, notified=0;
  const control = { willValidate:true, validity:{valid:false}, parentElement:details,
    getAttribute:key=>attributes[key], setAttribute:(key,value)=>attributes[key]=value, removeAttribute:key=>delete attributes[key], focus:()=>focused=true };
  const form = { querySelectorAll:()=>[control], checkValidity:()=>false, querySelector:()=>control, reportValidity:()=>reported=true };
  assert.equal(await validateSetupForm(form,()=>notified++),false);
  assert.equal(attributes['aria-invalid'],'true');assert.equal(attributes['aria-describedby'],'field-help setup-error');assert.equal(details.open,true);
  assert.equal(focused,true);assert.equal(reported,false);assert.equal(notified,1);
  control.validity.valid=true;form.checkValidity=()=>true;
  assert.equal(await validateSetupForm(form,()=>notified++),true);
  assert.equal(attributes['aria-invalid'],undefined);assert.equal(attributes['aria-describedby'],'field-help');assert.equal(notified,1);
});
test('Test Studio without a visible setup form preserves saved configuration path',async()=>{
  assert.equal(await validateSetupForm(null,()=>assert.fail()),true);
});

test('invalid feedback is rendered before field focus and avoids a competing native popup', async()=>{
  let rendered=false,focused=false;
  const control={willValidate:true,validity:{valid:false},parentElement:null,getAttribute:()=>null,setAttribute:()=>{},removeAttribute:()=>{},focus:()=>{assert.equal(rendered,true);focused=true;}};
  const form={querySelectorAll:()=>[control],checkValidity:()=>false,querySelector:()=>control,reportValidity:()=>assert.fail('native popup competes with accessible error')};
  assert.equal(await validateSetupForm(form,async()=>{await Promise.resolve();rendered=true;}),false);
  assert.equal(focused,true);
});
