import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {createRequire} from 'node:module';
import vm from 'node:vm';
const require = createRequire(import.meta.url);
const ts = require('typescript');
function app(search, saved, denied = false) {
  const storage = new Map(saved ? [['assistant-tenant', saved]] : []);
  const headers = [];
  const source = readFileSync(new URL('../src/services/api.ts', import.meta.url), 'utf8').replaceAll('import.meta.env', '({})');
  const js = ts.transpileModule(source, {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2022}}).outputText;
  const exports = {};
  vm.runInNewContext(js, {
    exports, URLSearchParams, Error,
    window:{location:{search}},
    sessionStorage:{getItem:k=>storage.get(k),setItem:(k,v)=>storage.set(k,v)},
    require:name=>name==='vue' ? {ref:value=>({value}),watch:()=>{}} : name==='./i18n' ? {uiLocale:{value:'en-US'},t:k=>k} : {},
    fetch:async(url, options)=>{
      if(url.endsWith('/api/demo/login')) return {ok:true,json:async()=>({tenant_id:'smilecare-demo',access_token:'fake'})};
      headers.push(options.headers['X-Tenant-ID']);
      const forbidden=denied && options.headers['X-Tenant-ID']==='concierge';
      return {ok:!forbidden,status:forbidden?403:200,json:async()=>forbidden?{code:'forbidden'}:{}};
    },
  });
  return {exports,headers};
}
test('tenant-specific link wins over a stale clinic selection on demo login',async()=>{
  const a=app('?tenant=concierge','smilecare-demo');
  await a.exports.connectDemo('demo','fake');
  assert.equal(a.exports.tenantId.value,'concierge');
  assert.deepEqual(a.headers,['concierge']);
});
test('demo re-login retains an authorized selected organization',async()=>{
  const a=app('','concierge'); await a.exports.connectDemo('demo','fake');
  assert.equal(a.exports.tenantId.value,'concierge');
});
test('a tenant hint cannot bypass server authorization',async()=>{
  const a=app('?tenant=concierge','smilecare-demo',true); await a.exports.connectDemo('demo','fake');
  assert.equal(a.exports.tenantId.value,'smilecare-demo');
  assert.deepEqual(a.headers,['concierge','smilecare-demo']);
});
