import test from 'node:test';
import assert from 'node:assert/strict';
import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
test('production owner Google mode rejects demo or conflicting Auth0 configuration',()=>{
  const script=fileURLToPath(new URL('../scripts/validate-production-auth-config.mjs',import.meta.url));
  const env={...process.env,VITE_GOOGLE_LOGIN:'true',VITE_LOCAL_DEMO_LOGIN:'',VITE_AUTH0_DOMAIN:'',VITE_AUTH0_CLIENT_ID:'',VITE_AUTH0_AUDIENCE:''};
  assert.equal(spawnSync(process.execPath,[script],{env}).status,0);
  for(const extra of [{VITE_LOCAL_DEMO_LOGIN:'true'},{VITE_AUTH0_DOMAIN:'identity.example'}]) assert.equal(spawnSync(process.execPath,[script],{env:{...env,...extra}}).status,1);
  assert.equal(spawnSync(process.execPath,[script],{env:{...env,VITE_GOOGLE_LOGIN:'false'}}).status,1);
});
