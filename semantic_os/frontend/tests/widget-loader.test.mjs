import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import test from 'node:test';
const source=readFileSync(new URL('../../widget/v1.js',import.meta.url),'utf8');
class Node extends EventTarget {
  constructor(tag){super();this.tag=tag;this.dataset={};this.children=[];this.attributes={};this.hidden=false;if(tag==='iframe')this.contentWindow={sent:[],postMessage(data,target){this.sent.push({data,target});}};}
  append(...nodes){for(const node of nodes){node.parentElement=this;this.children.push(node);}}
  attachShadow(){this.shadow=new Node('shadow');return this.shadow;}
  setAttribute(key,value){this.attributes[key]=value;}
  remove(){if(this.parentElement)this.parentElement.children=this.parentElement.children.filter(node=>node!==this);}
  focus(){}
}
function fixture(mode='embedded',fetcher){
  const script=new Node('script'),body=new Node('body'),window=new EventTarget();script.src='https://widget.example/widget/assets/v1.js';script.dataset={assistantId:'wdg_11111111111111111111111111111111',mode,locale:'bg-BG'};body.append(script);
  const calls=[];const context={document:{currentScript:script,body,readyState:'complete',createElement:tag=>new Node(tag)},window,URL,Event,CustomEvent,AbortController,location:{origin:'https://ontelyx.tech'},navigator:{language:'bg-BG'},setTimeout:()=>1,clearTimeout:()=>{},fetch:fetcher||((url,options)=>{calls.push({url,options});return Promise.resolve({ok:true,json:async()=>({ticket:'one-use-ticket-only',default_locale:'en-US'})});})};
  runInNewContext(source,context);
  const host=body.children.find(node=>node.tag==='div'),panel=host.shadow.children.find(node=>node.tag==='section');
  const frame=()=>panel.children.find(node=>node.tag==='iframe');
  const message=(type,origin='https://widget.example',sender=frame()?.contentWindow,extra={})=>{const event=new Event('message');Object.assign(event,{origin,source:sender,data:{namespace:'testmid-widget-v1',type,public_id:script.dataset.assistantId,nonce:'a'.repeat(32),...extra}});window.dispatchEvent(event);};
  return {script,body,host,panel,frame,message,calls};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
test('floating iframe is lazy and embedded presentation shares the same protocol',()=>{
  const floating=fixture('floating');assert.equal(floating.frame(),undefined);floating.host.shadow.children.find(node=>node.tag==='button').dispatchEvent(new Event('click'));assert.ok(floating.frame());
  const embedded=fixture();assert.ok(embedded.frame());assert.equal(embedded.panel.dataset.embedded,'true');assert.match(embedded.frame().attributes.sandbox,/allow-scripts allow-same-origin/);assert.doesNotMatch(embedded.frame().attributes.sandbox,/allow-top-navigation/);
});
test('wrong window/origin/schema and ready replay cannot acquire another ticket',async()=>{
  const f=fixture();f.message('ready','https://evil.example');f.message('ready','https://widget.example',{});f.message('ready',undefined,undefined,{unknown:'injection'});assert.equal(f.calls.length,0);
  f.message('ready');f.message('ready');await settle();assert.equal(f.calls.length,1);assert.equal(f.frame().contentWindow.sent.length,1);
  const sent=f.frame().contentWindow.sent[0];assert.equal(sent.target,'https://widget.example');assert.equal(sent.data.ticket,'one-use-ticket-only');assert.equal(sent.data.session_token,undefined);
});
test('readiness is relayed only by the bound iframe after redemption',async()=>{
  const f=fixture();let ready=0;f.script.addEventListener('testmid-widget-ready',()=>ready++);f.message('session-ready');assert.equal(ready,0);
  f.message('ready');await settle();assert.equal(ready,0);f.message('session-ready');assert.equal(ready,1);
});
test('teardown aborts pending bootstrap and removes the host/listener',async()=>{
  let resolve;const f=fixture('embedded',()=>new Promise(done=>resolve=done));f.message('ready');const frame=f.frame();f.script.dispatchEvent(new Event('testmid-widget-destroy'));
  resolve({ok:true,json:async()=>({ticket:'discarded'})});await settle();assert.equal(f.body.children.includes(f.host),false);assert.equal(frame.contentWindow.sent.length,0);
});
test('embedded expiry and clear are scoped recovery signals, without credentials',async()=>{
  const f=fixture();let expired=0,reset=0;f.script.addEventListener('testmid-widget-expired',()=>expired++);f.script.addEventListener('testmid-widget-reset',()=>reset++);
  f.message('ready');await settle();f.message('session-ready');f.message('restart');f.message('session-cleared');assert.equal(expired,1);assert.equal(reset,1);
});
