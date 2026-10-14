import test from 'node:test';
import assert from 'node:assert/strict';
import {customerAuthorizationURL} from '../src/services/customer-authorization.mjs';
const base='https://accounts.google.com/o/oauth2/v2/auth?client_id=synthetic-client&state=synthetic-state&response_type=code&redirect_uri='+encodeURIComponent('https://staging.example.invalid/backend/api/connectors/oauth/google/callback');
test('customer authorization accepts the exact server provider endpoint and HTTPS callback',()=>{
  assert.equal(customerAuthorizationURL(base,'google'),base);
});
test('customer authorization refuses forged hosts, provider mixup and credential-bearing URLs',()=>{
  for(const value of [base.replace('accounts.google.com','attacker.example'),base.replace('https:','http:'),base.replace('accounts.google.com','accounts.google.com.attacker.example'),base.replace('accounts.google.com','user:password@accounts.google.com'),base+'#hidden'])assert.throws(()=>customerAuthorizationURL(value,'google'));
  assert.throws(()=>customerAuthorizationURL(base,'outlook'));
  assert.throws(()=>customerAuthorizationURL(base.replace('response_type=code','response_type=token'),'google'));
});
test('customer authorization refuses redirected callback secrets and wrong provider callback',()=>{
  const url=new URL(base);
  for(const callback of ['http://localhost/backend/api/connectors/oauth/google/callback','https://staging.example.invalid/backend/api/connectors/oauth/hubspot/callback','https://staging.example.invalid/backend/api/connectors/oauth/google/callback?secret=synthetic']){
    url.searchParams.set('redirect_uri',callback);assert.throws(()=>customerAuthorizationURL(url.href,'google'));
  }
});
