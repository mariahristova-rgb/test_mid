import { labels } from './catalog.js';
const id = document.querySelector('meta[name="public-id"]').content;
const parentOrigin = document.querySelector('meta[name="parent-origin"]').content;
const initial = document.querySelector('meta[name="initial-locale"]').content;
const nonce = Array.from(crypto.getRandomValues(new Uint8Array(16)), v => v.toString(16).padStart(2, '0')).join('');
const byId = name => document.getElementById(name);
let locale = initial === 'bg-BG' ? 'bg-BG' : 'en-US', token = '', privacyToken = '', pending = null, busy = false, admitted = false, human = false, explicitLocale = initial !== 'auto';
const translated = key => labels[locale][key];
let privacyNotices = {};
let concierge=null;
let pendingBookingReference='',bookingDeadline=0;
const seenHuman = new Set();
async function refreshHuman() {
  if (!token || (!human && !pendingBookingReference) || busy || document.hidden || !navigator.onLine) return;
  if(pendingBookingReference && Date.now()>bookingDeadline){pendingBookingReference='';byId('error').textContent=translated('failed');if(!human)return;}
  try { const history = await api('history'); for (const message of history.messages) { if ((message.from_human || pendingBookingReference && message.booking_reference===pendingBookingReference) && !seenHuman.has(message.id)) { seenHuman.add(message.id); bubble(message.content, 'assistant'); if(message.booking_reference===pendingBookingReference && message.booking_final!==false)pendingBookingReference=''; } } }
  catch (error) { if (error.status === 401 || error.status === 403) {token='';restart();controls();} }
}
setInterval(() => void refreshHuman(), 5000);
function language(value) {
  locale = value; document.documentElement.lang = value; byId('locale').value = value;
  document.title=translated('assistant');
  byId('input').placeholder=value==='bg-BG'?'Задайте въпрос…':'Ask a question…';
  for (const element of document.querySelectorAll('[data-label]')) element.textContent = translated(element.dataset.label);
  if(privacyNotices[value]) byId('privacy').textContent=privacyNotices[value];
  concierge?.language();
}
function state(key) { byId('state').textContent = translated(key); }
function parentStatus(type) { window.parent.postMessage({namespace:'testmid-widget-v1',type,public_id:id,nonce},parentOrigin); }
function bubble(text, role) { const node = document.createElement('p'); node.className = 'bubble ' + role; node.textContent = text; byId('messages').append(node); node.scrollIntoView({ block: 'nearest' }); }
async function api(path, data, credential = token) {
  const response = await fetch('/widget/' + path + '/' + id, { method: data ? 'POST' : 'GET', credentials: 'omit',
    headers: { 'Content-Type': 'application/json', ...(credential ? { Authorization: 'Bearer ' + credential } : {}), 'X-UI-Locale': locale }, body: data ? JSON.stringify(data) : undefined });
  if (!response.ok) { const error = new Error('widget'); error.status = response.status; try{error.code=(await response.json()).code;}catch{} throw error; }
  return response.json();
}
function controls() { byId('send').disabled = busy || !token || human || !!pending; byId('confirm').disabled = busy || !token || !!pending; byId('human').disabled = busy || !token || human || !!pending; }
window.addEventListener('message', async event => {
  const data = event.data;
  if (event.source !== window.parent || event.origin !== parentOrigin || !data || typeof data !== 'object'
    || data.namespace !== 'testmid-widget-v1' || data.type !== 'admit' || data.public_id !== id || data.nonce !== nonce || admitted
    || !['bg-BG','en-US'].includes(data.locale) || typeof data.ticket !== 'string'
    || Object.keys(data).some(key => !['namespace','type','public_id','nonce','ticket','locale'].includes(key))) return;
  admitted = true;
  try {
    language(data.locale);
    try { const saved = JSON.parse(localStorage.getItem('testmid-language-' + id) || 'null'); if (saved?.consent && ['bg-BG','en-US'].includes(saved.locale)) { language(saved.locale); explicitLocale=true; byId('remember').checked = true; } } catch { /* Storage may be unavailable. */ }
    const session = await api('redeem', { ticket: data.ticket, parent_origin: parentOrigin, locale });
    token = session.session_token; privacyToken = token; privacyNotices=session.privacy_notices || {[locale]:session.privacy_notice}; language(locale);
    byId('analytics-control').hidden=!session.analytics_enabled;
    if(!session.native_booking_enabled && !session.concierge_enabled){byId('technical-notice').setAttribute('data-label','faqOnly');byId('technical-notice').textContent=translated('faqOnly');}
    if(session.concierge_enabled){
      const module=await import('./concierge.js');concierge=module.startConcierge({api,locale:()=>locale,bubble,send,id});
      byId('welcome').hidden=false;byId('technical-notice').hidden=true;concierge.language();
    }
    if(session.logo_url) { byId('logo').src=session.logo_url; byId('logo').hidden=false; }
    bubble(session.greeting, 'assistant'); state('ready'); byId('input').focus();
    parentStatus('session-ready');
  } catch { byId('error').textContent = translated('error'); parentStatus('session-error'); }
  controls();
});
async function send(retry = false, override) {
  if (busy || !token || human) return;
  if (!retry) {
    const content = override || byId('input').value.trim(); if (!content || pending) return;
    pending = { content, event_id: crypto.randomUUID(), locale:explicitLocale ? locale : null }; bubble(content, 'user'); byId('input').value = '';
  }
  busy = true; byId('error').textContent = ''; state('sending'); controls();
  try {
    const result = await api('messages', pending); pending = null;
    if(result.tool_result==='appointment_pending' && result.booking_reference){pendingBookingReference=result.booking_reference;bookingDeadline=Date.now()+300000;} bubble(result.response, 'assistant');
    if(['bg-BG','en-US'].includes(result.locale)) language(result.locale);
    human = result.human_requested; byId('confirm').hidden = result.booking_status !== 'awaiting_confirmation'; byId('retry').hidden = true; state(human ? 'handoff' : 'ready');
  } catch (error) { const expired=error.status === 401 || error.status === 403; byId('error').textContent = translated(expired ? 'expired' : 'failed'); byId('retry').hidden = expired; if (expired) {token = '';restart();} }
  finally { busy = false; controls(); }
}
byId('composer').addEventListener('submit', event => { event.preventDefault(); void send(); });
byId('retry').addEventListener('click', () => void send(true));
byId('confirm').addEventListener('click', () => void send(false, translated('confirmText')));
byId('human').addEventListener('click', () => void send(false, translated('humanText')));
function close() { window.parent.postMessage({ namespace:'testmid-widget-v1',type:'close',public_id:id,nonce },parentOrigin); }
function restart() { window.parent.postMessage({ namespace:'testmid-widget-v1',type:'restart',public_id:id,nonce },parentOrigin); }
byId('close').addEventListener('click', close);
document.addEventListener('keydown', event => { if (event.key === 'Escape') close(); });
byId('locale').addEventListener('change', () => { language(byId('locale').value); explicitLocale=true; if (byId('remember').checked) savePreference(); });
function savePreference() { try { if(byId('remember').checked) {explicitLocale=true;localStorage.setItem('testmid-language-' + id, JSON.stringify({consent:true,locale}));} else localStorage.removeItem('testmid-language-' + id); } catch { /* No storage is required for chat. */ } }
byId('remember').addEventListener('change', savePreference);
byId('analytics-consent').addEventListener('change',async()=>{
  if(!token)return;
  const box=byId('analytics-consent');box.disabled=true;
  try{await api('analytics-consent',{allowed:box.checked});}
  catch{byId('error').textContent=translated('analyticsError');}
  finally{box.disabled=false;}
});
byId('clear').addEventListener('click', async () => {
  if (!byId('clear-confirm').checked) { byId('error').textContent = translated('consent'); return; }
  if (busy || !privacyToken) return; busy = true; controls();
  try { await api('clear', { confirmed:true },privacyToken); token=''; privacyToken=''; pending=null; pendingBookingReference=''; byId('messages').replaceChildren(); state('cleared'); restart(); parentStatus('session-cleared');} catch { byId('error').textContent=translated('error'); }
  finally { busy=false; controls(); }
});
window.addEventListener('offline', () => state('offline'));
window.addEventListener('online', () => state(pending ? 'failed' : human ? 'handoff' : 'ready'));
language(locale); state('connecting'); controls();
function viewport(){document.documentElement.style.setProperty('--viewport-height',(window.visualViewport?.height||window.innerHeight)+'px');}
window.visualViewport?.addEventListener('resize',viewport);window.addEventListener('resize',viewport);viewport();
window.parent.postMessage({ namespace:'testmid-widget-v1',type:'ready',public_id:id,nonce },parentOrigin);
