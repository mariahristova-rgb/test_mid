(() => {
  'use strict';
  const script = document.currentScript;
  if (!script) return;
  const id = script.dataset.assistantId;
  if (!/^wdg_[a-f0-9]{32}$/.test(id || '')) return;
  const base = new URL(script.src).origin;
  const preferred = script.dataset.locale || 'auto';
  const embedded = script.dataset.mode === 'embedded';
  const bg = preferred === 'bg-BG' || preferred === 'auto' && navigator.language.toLowerCase().startsWith('bg');
  const title = bg ? 'Чат с асистента' : 'Chat with assistant';
  const controller = new AbortController();
  let disposed = false, host, timer;
  const notify = type => script.dispatchEvent(new CustomEvent('testmid-widget-' + type));
  script.addEventListener('testmid-widget-destroy', () => { disposed = true; controller.abort(); clearTimeout(timer); host?.remove(); }, { once:true });
  const mount = () => {
    if(disposed) return;
    host = document.createElement('div');
    const root = host.attachShadow({ mode: 'closed' });
    const css = document.createElement('link'); css.rel = 'stylesheet'; css.href = base + '/widget/assets/loader.css';
    const launcher = document.createElement('button'); launcher.type = 'button'; launcher.textContent = title;
    launcher.setAttribute('aria-expanded', 'false');
    const panel = document.createElement('section'); panel.hidden = !embedded;
    panel.setAttribute('role', embedded ? 'region' : 'dialog'); panel.setAttribute('aria-label', title);
    if(embedded) panel.dataset.embedded = 'true';
    const status = document.createElement('p'); status.setAttribute('role', 'status');
    root.append(css); if(!embedded) root.append(launcher); root.append(panel);
    (embedded ? script.parentElement : document.body).append(host);
    let frame, nonce, opening = false, restart = false, ready = false;
    const close = () => { if(embedded) notify('close'); else {panel.hidden = true; launcher.setAttribute('aria-expanded', 'false'); launcher.focus();} };
    const unavailable = () => { restart=true; status.textContent=bg?'Чатът не е достъпен. Опитайте по-късно.':'Chat unavailable. Try later.'; notify('error'); };
    const open = () => {
      if (!embedded && !panel.hidden) { close(); return; }
      panel.hidden = false; launcher.setAttribute('aria-expanded', 'true');
      if(frame && restart) {frame.remove();frame=null;nonce=null;restart=false;opening=false;ready=false;}
      if (frame) { frame.focus(); return; }
      status.textContent = bg ? 'Свързване…' : 'Connecting…'; panel.append(status);
      frame = document.createElement('iframe'); frame.title = title;
      frame.setAttribute('sandbox', 'allow-scripts allow-same-origin allow-popups allow-popups-to-escape-sandbox');
      frame.setAttribute('allow', "microphone 'none'; camera 'none'; geolocation 'none'");
      frame.referrerPolicy = 'no-referrer';
      frame.src = base + '/widget/frame/' + id + '?parent_origin=' + encodeURIComponent(location.origin) + '&locale=' + encodeURIComponent(preferred);
      panel.append(frame);
      const current = frame; clearTimeout(timer);
      timer=setTimeout(() => {if(!disposed && frame===current && !ready) unavailable();},15000);
    };
    launcher.addEventListener('click',open,{signal:controller.signal});
    window.addEventListener('message', async event => {
      const data = event.data;
      if (disposed || !frame || event.source !== frame.contentWindow || event.origin !== base || !data || typeof data !== 'object'
        || data.namespace !== 'testmid-widget-v1' || data.public_id !== id || !/^[a-f0-9]{32}$/.test(data.nonce || '')) return;
      if (Object.keys(data).some(key => !['namespace', 'public_id', 'nonce', 'type'].includes(key))) return;
      if(data.nonce===nonce) {
        if(data.type==='session-ready') {ready=true;clearTimeout(timer);status.remove();notify('ready');return;}
        if(data.type==='session-error') {unavailable();return;}
        if(data.type==='restart') {restart=true;if(embedded) notify('expired');return;}
        if(data.type==='session-cleared') {restart=true;if(embedded) notify('reset');return;}
        if(data.type==='close') {close();return;}
      }
      if (data.type !== 'ready' || opening || nonce) return;
      opening = true; const current=frame;
      try {
        const response = await fetch(base + '/widget/admission/' + id, { method: 'POST', credentials: 'omit', signal:controller.signal,
          headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ locale: ['bg-BG', 'en-US'].includes(preferred) ? preferred : 'auto' }) });
        if (!response.ok) throw new Error('admission');
        const admission = await response.json();
        if(disposed || frame!==current) return;
        const detected = navigator.language.toLowerCase();
        const locale = ['bg-BG', 'en-US'].includes(preferred) ? preferred : detected.startsWith('bg') ? 'bg-BG' : detected.startsWith('en') ? 'en-US' : admission.default_locale;
        nonce = data.nonce;
        frame.contentWindow.postMessage({ namespace: 'testmid-widget-v1', type: 'admit', public_id: id, nonce,
          ticket: admission.ticket, locale }, base);
        frame.focus();
      } catch {if(!disposed) unavailable();}
      finally { opening = false; }
    },{signal:controller.signal});
    root.addEventListener('keydown', event => { if (event.key === 'Escape') close(); },{signal:controller.signal});
    if(embedded) open();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount, { once: true,signal:controller.signal }); else mount();
})();
