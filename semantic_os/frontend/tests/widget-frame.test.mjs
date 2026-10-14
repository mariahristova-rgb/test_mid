import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {runInNewContext} from 'node:vm';
import test from 'node:test';

const source=readFileSync(new URL('../../widget/frame.js',import.meta.url),'utf8').replace("import { labels } from './catalog.js';",'');
const catalog=readFileSync(new URL('../../widget/catalog.js',import.meta.url),'utf8');
const labels=Function(catalog.replace('export const labels','const labels')+';return labels')();
class Element extends EventTarget {
  constructor(){super();this.value='';this.textContent='';this.children=[];this.dataset={};this.style={setProperty(){}};this.checked=false;this.disabled=false;this.focusCount=0;}
  append(node){this.children.push(node);}
  replaceChildren(){this.children=[];}
  setAttribute(key,value){this[key]=value;}
  scrollIntoView(){}
  focus(){this.focusCount++;}
}
function fixture(handler){
  const nodes=new Map(),window=new EventTarget(),document=new EventTarget(),calls=[];
  const node=id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id);};
  const values={'public-id':'wdg_'+'1'.repeat(32),'parent-origin':'https://synthetic.example','initial-locale':'en-US'};
  Object.assign(document,{hidden:false,documentElement:new Element(),querySelector:selector=>({content:values[selector.match(/name="([^"]+)"/)[1]]}),querySelectorAll:()=>[],getElementById:node,createElement:()=>new Element()});
  Object.assign(window,{parent:{sent:[],postMessage(data,target){this.sent.push({data,target});}},innerHeight:640});
  const context={labels,document,window,navigator:{onLine:true},crypto:{getRandomValues:array=>array.fill(7),randomUUID:()=> 'synthetic-event'},localStorage:{getItem:()=>null,setItem(){},removeItem(){}},setInterval:()=>1,fetch:async(url,options)=>{
    const call={url,options,payload:options.body?JSON.parse(options.body):undefined};calls.push(call);
    if(url.includes('/redeem/'))return {ok:true,json:async()=>({session_token:'synthetic-private-capability',greeting:'Hello',native_booking_enabled:true})};
    return handler(call);
  }};
  runInNewContext(source,context);
  async function admit(){
    const event=new Event('message');Object.assign(event,{source:window.parent,origin:values['parent-origin'],data:{namespace:'testmid-widget-v1',type:'admit',public_id:values['public-id'],nonce:window.parent.sent[0].data.nonce,ticket:'synthetic-ticket',locale:'en-US'}});
    window.dispatchEvent(event);await settle();
  }
  const submit=async()=>{node('composer').dispatchEvent(new Event('submit',{cancelable:true}));await settle();};
  return {window,node,calls,admit,submit};
}
const settle=()=>new Promise(resolve=>setImmediate(resolve));
const success=(response='Confirmed')=>({ok:true,json:async()=>({response,locale:'en-US',booking_status:'confirmed',human_requested:false})});

test('network reconnect preserves original action and requires explicit retry',async()=>{
  let attempts=0;
  const f=fixture(()=>{if(++attempts===1)throw new TypeError('synthetic network failure');return success();});
  await f.admit();f.node('input').value='Book a demo';await f.submit();
  assert.equal(f.node('retry').hidden,false);assert.equal(f.node('send').disabled,true);
  f.window.dispatchEvent(new Event('offline'));f.window.dispatchEvent(new Event('online'));
  assert.equal(attempts,1);
  f.node('retry').dispatchEvent(new Event('click'));await settle();
  const requests=f.calls.filter(c=>c.url.includes('/messages/'));
  assert.equal(requests.length,2);assert.deepEqual(requests[0].payload,requests[1].payload);
  assert.equal(f.node('messages').children.filter(n=>n.className==='bubble user').length,1);
  assert.equal(f.node('retry').hidden,true);assert.equal(f.node('send').disabled,false);
  assert.ok(f.node('input').focusCount>0);
});

test('expired capability requests recovery without replaying the write',async()=>{
  const f=fixture(()=>({ok:false,status:401,json:async()=>({code:'unauthorized'})}));
  await f.admit();f.node('input').value='Confirm';await f.submit();
  assert.equal(f.node('send').disabled,true);assert.equal(f.node('retry').hidden,true);
  assert.ok(f.window.parent.sent.some(m=>m.data.type==='restart'));
  f.window.dispatchEvent(new Event('online'));f.node('retry').dispatchEvent(new Event('click'));await settle();
  assert.equal(f.calls.filter(c=>c.url.includes('/messages/')).length,1);
  assert.ok(f.window.parent.sent.every(m=>!JSON.stringify(m.data).includes('synthetic-private-capability')));
});

test('human handoff prevents subsequent automatic messages',async()=>{
  const f=fixture(()=>({ok:true,json:async()=>({response:'Operator requested',locale:'en-US',human_requested:true})}));
  await f.admit();f.node('input').value='Human please';await f.submit();
  f.node('input').value='Another question';await f.submit();
  assert.equal(f.calls.filter(c=>c.url.includes('/messages/')).length,1);
  assert.equal(f.node('send').disabled,true);
});

test('clear needs explicit consent and removes pending retry authority',async()=>{
  const f=fixture(()=>success());await f.admit();
  f.node('clear').dispatchEvent(new Event('click'));await settle();
  assert.equal(f.calls.filter(c=>c.url.includes('/clear/')).length,0);
  f.node('clear-confirm').checked=true;f.node('clear').dispatchEvent(new Event('click'));await settle();
  assert.equal(f.calls.filter(c=>c.url.includes('/clear/')).length,1);
  assert.equal(f.node('send').disabled,true);assert.equal(f.node('messages').children.length,0);
  f.node('input').value='After clear';await f.submit();
  assert.equal(f.calls.filter(c=>c.url.includes('/messages/')).length,0);
});
