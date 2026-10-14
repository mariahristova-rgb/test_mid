import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {parse,compileScript} from '@vue/compiler-sfc';
import ts from 'typescript';
import {createSSRApp} from 'vue';
import {renderToString} from 'vue/server-renderer';

const source=readFileSync(new URL('../src/components/ConnectorCatalog.vue',import.meta.url),'utf8');
test('BG/EN compiled catalog distinguishes planned connectors and simulated states without effects',async()=>{
  const {descriptor}=parse(source);
  const compiled=compileScript(descriptor,{id:'catalog-test',inlineTemplate:true});
  for(const locale of ['bg-BG','en-US']) {
    const labels=JSON.parse(readFileSync(new URL(`../src/locales/${locale}.json`,import.meta.url),'utf8'));
    const workspaceSource=readFileSync(new URL('../src/components/ConnectorWorkspace.vue',import.meta.url),'utf8');
    const workspace=compileScript(parse(workspaceSource).descriptor,{id:'workspace-test',inlineTemplate:true}).content
      .replace("import {request} from '../services/api';",'const request=()=>{throw new Error("Unexpected network");};')
      .replace("import {t} from '../services/i18n';",`const labels=${JSON.stringify(labels)}; const t=(key)=>labels[key]??key;`)
      .replaceAll('from "vue"',`from ${JSON.stringify(import.meta.resolve('vue'))}`)
      .replaceAll("from 'vue'",`from ${JSON.stringify(import.meta.resolve('vue'))}`);
    const workspaceCode=ts.transpileModule(workspace,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
    const workspaceUrl='data:text/javascript;base64,'+Buffer.from(workspaceCode).toString('base64');
    const script=compiled.content.replace("import {t} from '../services/i18n';",`const labels=${JSON.stringify(labels)}; const t=(key)=>labels[key]??key;`)
      .replace("from './ConnectorWorkspace.vue'",'from '+JSON.stringify(workspaceUrl))
      .replaceAll('from "vue"',`from ${JSON.stringify(import.meta.resolve('vue'))}`)
      .replaceAll("from 'vue'",`from ${JSON.stringify(import.meta.resolve('vue'))}`);
    const code=ts.transpileModule(script,{compilerOptions:{module:ts.ModuleKind.ESNext,target:ts.ScriptTarget.ES2022}}).outputText;
    const component=(await import('data:text/javascript;base64,'+Buffer.from(code).toString('base64'))).default;
    const html=await renderToString(createSSRApp(component));
    assert.equal(html.split(labels.connectorComingSoon).length-1,4);
    assert.ok(html.includes(labels.connectorSimulationHelp));
    assert.ok(html.includes('for="connector-demo-state"'));
    assert.ok(html.includes('id="connector-demo-state"'));
    assert.ok(html.includes('role="status" aria-live="polite" aria-atomic="true"'));
    for(const state of ['disconnected','connected','reauthorization','degraded']) assert.ok(html.includes(labels['connectorState_'+state]));
    for(const price of ['connectorPriceSimple','connectorPriceAdvanced','connectorPriceEnterprise']) assert.ok(html.includes(labels[price]));
    assert.ok(html.includes(labels.connectorLoad));
    assert.ok(!html.includes(labels.connectorOAuthFixture));
    assert.ok(!/<a\b|<input/i.test(html));
  }
  assert.ok(!/request\(|fetch\(|localStorage|window\.|\/api\//.test(source));
  const ownerView=readFileSync(new URL('../src/views/GoogleWorkspaceView.vue',import.meta.url),'utf8');
  assert.ok(ownerView.indexOf('<ConnectorCatalog />')>ownerView.indexOf('<template v-if="allowed">'));
  assert.ok(ownerView.includes("access.value.user?.role==='admin'"));
});
