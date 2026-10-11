<script setup lang="ts">
import InboxQueue from "../components/InboxQueue.vue";
import { computed, onMounted, onUnmounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import { request } from '../services/api';
import { t, date, number, uiLocale, type Locale } from '../services/i18n';
import EmptyState from '../components/EmptyState.vue';
import MessagingConnections from '../components/MessagingConnections.vue';
import { connectVoice, sendSyntheticAudio } from '../services/voiceStream';
import { workspaceReads, inboxToolNames, messageSpeaker } from '../services/workspace.mjs';
import ConversationDebugger from '../components/ConversationDebugger.vue';
import AssistantStudio from '../components/AssistantStudio.vue';
const route = useRoute();
const page = computed(() => String(route.meta.page || 'dashboard'));
const channels = ['voice', 'email', 'whatsapp', 'sms', 'web_chat'];
const data = ref<any>({}), assistants = ref<any[]>([]), agents = ref<any[]>([]), conversations = ref<any[]>([]), contacts = ref<any[]>([]), appointments = ref<any[]>([]), calls = ref<any[]>([]), approvals = ref<any[]>([]), connections = ref<any[]>([]), followUps = ref<any[]>([]), audit = ref<any[]>([]);
const messages = ref<any[]>([]), current = ref(''), assistantId = ref('default'), contactId = ref('');
const selectedConversation = ref<any>(null);
const locale = ref<Locale>('bg-BG'), channel = ref('web_chat'), text = ref(''), error = ref(''), notice = ref(''), busy = ref(false);
const conversationLanguage = ref<'auto' | Locale>('auto');
const tool = ref(''), contactName = ref(''), startsAt = ref(''), duration = ref(30), appointmentId = ref(''), recipient = ref(''), sendChannel = ref('email'), title = ref(''), dueAt = ref(''), reason = ref('');
const newContact = ref({ name: '', address: '', preferred_locale: 'bg-BG', sms_opt_out: false });
const inboxChannel = ref(''), inboxStatus = ref(''), inboxLocale = ref(''), inboxAssistant = ref(''), inboxDate = ref('');
const nextInboxCursor = ref<number|null>(null);
function inboxPath(cursor?: number) {
  const parameters = new URLSearchParams({limit:'50'});
  for(const [key,value] of [['channel',inboxChannel.value],['status',inboxStatus.value],['locale',inboxLocale.value],['assistant_id',inboxAssistant.value],['local_day',inboxDate.value]]) if(value) parameters.set(key,value);
  if(cursor != null) parameters.set('cursor',String(cursor));
  return '/api/inbox?' + parameters;
}
async function reloadInbox(append = false) {
  const result = await request(inboxPath(append ? nextInboxCursor.value ?? undefined : undefined));
  conversations.value = append ? [...conversations.value,...result.items] : result.items;
  nextInboxCursor.value = result.next_cursor;
}
const attachmentIds = ref<string[]>([]);
const visibleConversations = computed(() => conversations.value.filter(c => (!inboxChannel.value || c.channel === inboxChannel.value)
  && (!inboxStatus.value || c.status === inboxStatus.value) && (!inboxLocale.value || c.active_locale === inboxLocale.value)
  && (!inboxAssistant.value || c.assistant_id === inboxAssistant.value) && (!inboxDate.value || c.last_message_at && new Intl.DateTimeFormat('en-CA', { timeZone: tz.value, year: 'numeric', month: '2-digit', day: '2-digit' }).format(new Date(c.last_message_at)) === inboxDate.value)));
const canConfigure = computed(() => data.value.user?.role === 'admin');
const canExecute = computed(() => ['admin', 'operator'].includes(data.value.user?.role));
const tz = computed(() => data.value.tenant?.timezone || 'Europe/Sofia');
const pending = computed(() => approvals.value.filter(a => a.status === 'pending' && (!current.value || a.conversation_id === current.value)));
const toolNames = computed(() => (data.value.tools || []).map((x: any) => x.name));
const inboxTools = computed(() => inboxToolNames(data.value.tools||[],assistants.value.find(a=>a.id===(selectedConversation.value?.assistant_id||assistantId.value))?.allowed_tools||[]));
const paused = computed(() => selectedConversation.value?.human_escalation);
const closed = computed(() => selectedConversation.value?.status === 'closed');
const settings = ref<any>({});
const templates = ref<any[]>([]), jobs = ref<any[]>([]), users = ref<any[]>([]);
const newUser = ref({ subject: '', role: 'viewer', enabled: true, preferred_locale: 'en-US' });
const streamCall = ref(''), streamReady = ref(false), streamResponse = ref('');
const callActivity = ref<any>(null);
const diagnosticConversation = ref('');
async function showCallActivity(id: string) { callActivity.value = await request(`/api/calls/${id}/activity`); }
let stream: WebSocket | undefined, streamSequence = 0;
let inboxTimer: ReturnType<typeof setInterval> | undefined;
let polling = false;
let loadController: AbortController | undefined, loadEpoch = 0;
onUnmounted(() => { loadEpoch++; loadController?.abort(); stream?.close(); if (inboxTimer) clearInterval(inboxTimer); });
watch(page, () => { if (page.value !== 'calls') { stream?.close(); streamReady.value = false; streamCall.value = ''; } });

let inboxRevision = 0;
async function run(action: () => Promise<unknown>) { const revision = ++inboxRevision; busy.value = true; error.value = ''; notice.value = ''; try { await action(); } catch (e) { if(revision === inboxRevision && !(e instanceof Error && e.name === 'AbortError')) error.value = e instanceof Error && e.message ? e.message : t('error'); } finally { if(revision === inboxRevision) busy.value = false; } }
async function load() {
  loadController?.abort(); loadController = new AbortController(); const epoch = ++loadEpoch;
  const keys = workspaceReads(page.value);
  const results = await Promise.all(keys.map(key => request(key === 'inbox' ? inboxPath() : '/api/' + key,'GET',undefined,loadController?.signal)));
  if(epoch !== loadEpoch) return;
  const values = Object.fromEntries(keys.map((key,index) => [key,results[index]]));
  data.value = values.bootstrap;
  assistants.value = values.assistants || []; agents.value = values.agents || []; conversations.value = values.inbox?.items || [];
  nextInboxCursor.value = values.inbox?.next_cursor ?? null;
  contacts.value = values.contacts || []; appointments.value = values.appointments || []; calls.value = values.calls || [];
  approvals.value = values.approvals || []; connections.value = values.connections || []; followUps.value = values['follow-up-tasks'] || [];
  const tenant = data.value.tenant;
  settings.value = { default_locale: tenant.default_locale, timezone: tenant.timezone, usage_limit: tenant.usage_limit, retention_days: tenant.retention_days, recording_enabled: tenant.recording_enabled, transcripts_enabled: tenant.transcripts_enabled, notice_acknowledged: false };
  if (!assistants.value.some(a => a.id === assistantId.value)) assistantId.value = assistants.value[0]?.id || '';
  if (canConfigure.value && page.value === 'settings') {
    [audit.value, templates.value, jobs.value, users.value] = await Promise.all([request('/api/audit'), request('/api/templates'), request('/api/jobs'), request('/api/users')]);
  }
}
onMounted(() => {
  void run(async () => { await load(); if(page.value === 'inbox' && route.query.conversation) await openConversation(String(route.query.conversation)); });
  inboxTimer = setInterval(async () => {
    if (busy.value || polling) return;
    if (['calls', 'appointments', 'dashboard'].includes(page.value)) {
      const revision = inboxRevision;
      polling = true;
      try {
        const pollingPage = page.value;
        const selected = callActivity.value?.call.id;
        const [recentCalls, bookings, activity, snapshot] = await Promise.all([
          pollingPage === 'calls' ? request('/api/calls') : Promise.resolve(null),
          pollingPage === 'appointments' ? request('/api/appointments') : Promise.resolve(null),
          pollingPage === 'calls' && selected ? request(`/api/calls/${selected}/activity`) : Promise.resolve(null),
          pollingPage === 'dashboard' ? request('/api/bootstrap') : Promise.resolve(null)]);
        if (revision === inboxRevision && !busy.value && pollingPage === page.value) {
          if (recentCalls) calls.value = recentCalls;
          if (bookings) appointments.value = bookings;
          if (activity && selected === callActivity.value?.call.id) callActivity.value = activity;
          if (snapshot && page.value === 'dashboard') data.value = snapshot;
        }
      } catch (e) { error.value = e instanceof Error ? e.message : t('error'); }
      finally { polling = false; }
      return;
    }
    if (page.value !== 'inbox' || !current.value) return;
    const id = current.value;
    const revision = inboxRevision;
    polling = true;
    try {
      const [history, inbox, actions, selectedRows] = await Promise.all([request(`/api/conversations/${id}/messages`), request(inboxPath()), request('/api/approvals'),request('/api/inbox?conversation_id=' + encodeURIComponent(id))]);
      if (current.value === id && revision === inboxRevision && !busy.value) {
        messages.value = history; approvals.value = actions;
        selectedConversation.value = selectedRows[0] || null;
        const latestRows = new Map(inbox.items.map((row: any) => [row.id,row]));
        conversations.value = conversations.value.map(row => latestRows.get(row.id) || row);
      }
    } catch (e) { error.value = e instanceof Error ? e.message : t('error'); }
    finally { polling = false; }
  }, 2000);
});
watch(page, () => { callActivity.value = null; diagnosticConversation.value = ''; void run(async () => { await load(); if(page.value === 'inbox' && route.query.conversation) await openConversation(String(route.query.conversation)); }); });
async function refreshConversationData() {
  await reloadInbox();
  [approvals.value, appointments.value, followUps.value] = await Promise.all([
    request('/api/approvals'), request('/api/appointments'), request('/api/follow-up-tasks')]);
}
async function refreshQueue() {
  const identity=current.value; const rows=await request("/api/inbox?conversation_id="+encodeURIComponent(identity));
  if(current.value===identity) selectedConversation.value=rows[0]||null;
}
async function openConversation(id: string) {
  let conversation = conversations.value.find(c => c.id === id);
  if(!conversation) { const found = await request('/api/inbox?conversation_id=' + encodeURIComponent(id)); conversation = found[0]; if(!conversation) throw new Error(t('not_found')); conversations.value.push(conversation); }
  current.value = id; if (conversation?.active_locale) locale.value = conversation.active_locale;
  selectedConversation.value = conversation;
  messages.value = await request(`/api/conversations/${id}/messages`);
}
watch([inboxChannel,inboxStatus,inboxLocale,inboxAssistant,inboxDate], () => { if(page.value === 'inbox' && data.value.user) void run(() => reloadInbox()); });
watch(() => route.query.conversation, value => { if(page.value === 'inbox' && value && data.value.user) void run(() => openConversation(String(value))); });
async function createConversation() { const conversation = await request('/api/conversations', 'POST', { assistant_id: assistantId.value, channel: channel.value, contact_id: contactId.value || null }); await refreshConversationData(); await openConversation(conversation.id); }
async function parsed(value: string) { return (await request('/api/dates/parse', 'POST', { value, locale: uiLocale.value })).iso; }
async function send() {
  if (!current.value) await createConversation();
  const args: any = {};
  if (['CheckAvailability', 'CreateAppointment', 'RescheduleAppointment'].includes(tool.value)) { args.starts_at = await parsed(startsAt.value); args.duration_minutes = duration.value; }
  if (['CreateAppointment', 'RescheduleAppointment'].includes(tool.value)) args.contact_name = contactName.value;
  if (['RescheduleAppointment', 'CancelAppointment'].includes(tool.value)) args.appointment_id = appointmentId.value;
  if (tool.value === 'SendMessage') Object.assign(args, { channel: sendChannel.value, recipient: recipient.value, content: text.value });
  if (tool.value === 'CreateFollowUpTask') Object.assign(args, { title: title.value, due_at: await parsed(dueAt.value) });
  if (tool.value === 'EscalateToHuman') args.reason = reason.value;
  const result = await request(`/api/conversations/${current.value}/messages`, 'POST', { content: text.value || t(tool.value), event_id: crypto.randomUUID(), locale: conversationLanguage.value === 'auto' ? null : conversationLanguage.value, tool: tool.value || null, arguments: args, attachment_ids: attachmentIds.value });
  notice.value = result.response; text.value = ''; attachmentIds.value = []; await refreshConversationData(); await openConversation(current.value);
}
async function approve(id: string) { const result = await request(`/api/approvals/${id}/confirm`, 'POST', { confirmed: true }); notice.value = result.response; await refreshConversationData(); if (current.value) await openConversation(current.value); }
async function saveAssistant(a: any) { const { id, tenant_id: _tenant, ...config } = a; await request('/api/assistants/' + id, 'PUT', config); notice.value = t('saved'); }
async function addAssistant() { await request('/api/assistants', 'POST', { name: t('assistant'), default_locale: locale.value }); await load(); }
async function saveAgent(a: any) { await request('/api/agents/' + a.id, 'PUT', { enabled: a.enabled, instructions: a.instructions, allowed_tools: a.allowed_tools, supported_locales: a.supported_locales }); notice.value = t('saved'); }
async function saveSettings() { await request('/api/settings', 'PUT', settings.value); await load(); notice.value = t('saved'); }
async function addContact() { await request('/api/contacts', 'POST', newContact.value); newContact.value.name = ''; newContact.value.address = ''; await load(); }
async function startCall() { await request('/api/calls', 'POST', { assistant_id: assistantId.value, locale: locale.value }); await load(); }
async function openVoice(call: any) {
  stream?.close(); streamCall.value = call.id; streamReady.value = false; streamResponse.value = ''; streamSequence = 0;
  stream = await connectVoice(call.id, event => {
    if (event.event === 'ready') streamReady.value = true;
    if (event.event === 'turn_result') {
      streamResponse.value = event.response;
      call.last_response = event.response; call.voice_locale = event.locale; call.status = event.status;
    }
    if (event.event === 'error') error.value = t(event.code) === event.code ? t('error') : t(event.code);
  });
  stream.onclose = () => { streamReady.value = false; void run(load); };
}
function sendVoice() { if (stream?.readyState === WebSocket.OPEN) { sendSyntheticAudio(stream, text.value, streamSequence++); text.value = ''; } }
async function callAction(call: any, action: string) { await request(`/api/calls/${call.id}/events`, 'POST', { action, locale: locale.value, text: text.value || t('message'), event_id: crypto.randomUUID() }); await load(); }
async function control(action: string) { await request(`/api/conversations/${current.value}/control`, 'POST', { action, confirmed: true }); await refreshConversationData(); await openConversation(current.value); }
async function humanReply() { await request(`/api/conversations/${current.value}/human-reply`, 'POST', { content: text.value, event_id: crypto.randomUUID(), confirmed: true }); text.value = ''; await refreshConversationData(); await openConversation(current.value); }
async function approveDraft(id: string) { await request(`/api/messages/${id}/approve-draft`, 'POST', { confirmed: true }); await openConversation(current.value); }
async function attach(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (file.size > 2_000_000) throw new Error(t('attachmentLimit'));
  if (!current.value) await createConversation();
  const encoded = await new Promise<string>((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(String(reader.result).split(',')[1]); reader.onerror = reject; reader.readAsDataURL(file); });
  const result = await request(`/api/conversations/${current.value}/attachments`, 'POST', { name: file.name, media_type: file.type || 'text/plain', data_base64: encoded });
  attachmentIds.value.push(result.storage_key); notice.value = t('quarantined');
}
async function saveTemplate(template: any) { await request('/api/templates/' + template.id, 'PUT', { body: template.body }); notice.value = t('saved'); }
async function addUser() { await request('/api/users', 'POST', newUser.value); newUser.value.subject = ''; await load(); }
function formatArgument(key: string, value: any) { if (key === 'starts_at' || key === 'due_at') return date(String(value), tz.value); return typeof value === 'object' ? JSON.stringify(value) : String(value); }
function providerStatus(provider: any) { return provider.state === 'MOCK' ? 'MOCK_ONLY' : provider.state === 'UNCONFIGURED' || provider.state === 'NOT_CONFIGURED' ? 'NOT_CONFIGURED' : provider.state === 'ERROR' ? 'ERROR' : 'CONFIGURED'; }
const argumentLabels: Record<string, string> = { starts_at: 'date', duration_minutes: 'duration', contact_name: 'contactName', appointment_id: 'id', channel: 'channel', recipient: 'recipient', content: 'message', title: 'task', due_at: 'dueAt', reason: 'reason' };
</script>
<template>
  <div class="page-heading">
<h1>{{ t(page) }}</h1><button :disabled="busy" @click="run(load)">
{{ t('refresh') }}
</button>
</div>
  <p class="banner">
{{ t('runtimeEvidenceNotice') }}
</p>
  <p v-if="error" class="error" role="alert">
{{ error }}
</p><p v-if="notice" class="success" role="status">
{{ notice }}
</p><p v-if="busy" role="status">
{{ t('busy') }}
</p>
  <template v-if="page === 'dashboard'">
    <div class="cards">
<article v-for="(value, key) in data.counts" :key="key">
<h2>{{ t(key === 'call_sessions' ? 'calls' : key === 'usage_records' ? 'usage' : key === 'conversations' ? 'inbox' : String(key)) }}</h2><strong class="metric">{{ number(Number(value)) }}</strong><span class="badge">{{ t('persistedCount') }}</span>
</article>
</div>
    <article>
<h2>{{ t('readinessReview') }}</h2><p>{{ t('voice_acceptance_blocked') }}</p><p>{{ t('countsNotSuccessRates') }}</p><RouterLink to="/testing">
{{ t('testAssistant') }}
</RouterLink>
</article>
    <article><h2>{{ t('languageSupport') }}</h2><p>{{ t('speechNotice') }}</p><p>{{ t('timezone') }}: {{ tz }}</p></article>
  </template>
  <template v-if="page === 'assistants'">
    <RouterLink v-if="canConfigure" class="action-link" to="/setup">
{{ t('guidedSetup') }}
</RouterLink>
    <button v-if="canConfigure" :disabled="busy" @click="run(addAssistant)">
{{ t('new') }}
</button>
    <article v-for="a in assistants" :key="a.id">
<h2>{{ a.name }}</h2><p>{{ t(a.status) }} · {{ t(a.llm_provider === 'mock' ? 'MOCK_ONLY' : 'CONFIGURED') }}</p><RouterLink :to="{path:'/setup',query:{assistant:a.id}}">
{{ t('editDraft') }}
</RouterLink> · <RouterLink to="/testing">
{{ t('testAssistant') }}
</RouterLink>
<AssistantStudio :assistant="a" :can-configure="canConfigure" :timezone="tz" />
<details>
<summary>{{ t('advancedDirectEditing') }}</summary><p class="banner">
{{ t('directEditingWarning') }}
</p>
<form @submit.prevent="run(() => saveAssistant(a))">
<fieldset :disabled="!canConfigure || busy">
<label>{{ t('name') }}<input v-model="a.name" required maxlength="120"></label><label>{{ t('description') }}<textarea v-model="a.description" maxlength="1000" /></label><label>{{ t('instructions') }}<textarea v-model="a.instructions" maxlength="8000" /></label><label>{{ t('defaultLocale') }}<select v-model="a.default_locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><div class="checks">
<label v-for="c in channels" :key="c"><input v-model="a.enabled_channels" type="checkbox" :value="c">{{ t(c) }}</label>
</div><label>{{ t('bookingDuration') }}<input v-model.number="a.booking_duration_minutes" type="number" min="5" max="480" required></label>
<h3>{{ t('voiceConfiguration') }}</h3>
<label>{{ t('telephonyProvider') }}<select v-model="a.voice_settings.telephony_provider"><option v-for="provider in ['mock','twilio','asterisk']" :key="provider" :value="provider">{{ t(provider === 'mock' ? 'MOCK' : provider) }}</option></select></label>
<label>{{ t('sttProvider') }}<select v-model="a.voice_settings.stt_provider"><option v-for="provider in ['mock','azure','faster_whisper']" :key="provider" :value="provider">{{ t(provider === 'mock' ? 'MOCK' : provider) }}</option></select></label>
<label>{{ t('ttsProvider') }}<select v-model="a.voice_settings.tts_provider"><option v-for="provider in ['mock','azure','piper','espeak_ng','bgtts38']" :key="provider" :value="provider">{{ t(provider === 'mock' ? 'MOCK' : provider) }}</option></select></label>
<label>{{ t('incomingNumber') }}<input v-model="a.voice_settings.incoming_phone_number" type="tel"></label>
<label>{{ t('callLanguage') }}<select v-model="a.voice_settings.locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label>
<div v-for="language in ['bg-BG', 'en-US']" :key="language">
<label>{{ t('voiceSelection') }} · {{ t(language) }}<input v-model="a.voice_settings.voices[language]" required></label><label>{{ t('greeting') }} · {{ t(language) }}<textarea v-model="a.voice_settings.greetings[language]" required /></label>
</div>
<label>{{ t('callTimeout') }}<input v-model.number="a.voice_settings.call_timeout_seconds" type="number" min="30" max="3600"></label>
<label>{{ t('silenceTimeout') }}<input v-model.number="a.voice_settings.silence_timeout_seconds" type="number" min="5" max="120"></label>
<label>{{ t('latencyLimit') }}<input v-model.number="a.voice_settings.max_latency_ms" type="number" min="500" max="120000"></label>
<label>{{ t('humanNumber') }}<input v-model="a.voice_settings.human_escalation_number" type="tel"></label>
<label class="check"><input v-model="a.voice_settings.recording" type="checkbox">{{ t('recording') }}</label>
<label class="check"><input v-model="a.voice_settings.transcript_storage" type="checkbox">{{ t('transcripts') }}</label>
<label>{{ t('retentionDays') }}<input v-model.number="a.voice_settings.transcript_retention_days" type="number" min="1" max="365"></label>
<label>{{ t('lawfulBasis') }}<select v-model="a.voice_settings.lawful_basis"><option v-for="basis in ['none', 'consent', 'contract', 'legitimate_interests']" :key="basis" :value="basis">{{ t(basis) }}</option></select></label>
<p>{{ t('speechNotice') }}</p><label>{{ t('status') }}<select v-model="a.status"><option value="active">{{ t('active') }}</option><option value="disabled">{{ t('disabled') }}</option></select></label><button>{{ t('save') }}</button>
</fieldset>
</form>
</details>
</article>
  </template>
  <template v-if="page === 'agents'">
    <article v-for="a in agents" :key="a.id">
<h2>{{ t(a.key) }}</h2><form @submit.prevent="run(() => saveAgent(a))">
<fieldset :disabled="!canConfigure || busy">
<label class="check"><input v-model="a.enabled" type="checkbox">{{ t('enabled') }}</label><label>{{ t('instructions') }}<textarea v-model="a.instructions" /></label><h3>{{ t('tools') }}</h3><label v-for="name in toolNames" :key="name" class="check"><input v-model="a.allowed_tools" type="checkbox" :value="name">{{ t(name) }}</label><button>{{ t('save') }}</button>
</fieldset>
</form>
</article>
  </template>
  <template v-if="page === 'inbox' || page === 'appointments'">
    <p v-if="page === 'inbox' && inboxTools.includes('CreateAppointment')">
{{ t('bookingHint') }}
</p>
    <details v-if="page === 'inbox'" class="inbox-filters">
<summary>{{ t('conversationFilters') }}</summary>
    <article class="controls">
      <label>{{ t('channel') }}<select v-model="inboxChannel"><option value="">{{ t('all') }}</option><option v-for="c in channels" :key="c" :value="c">{{ t(c) }}</option></select></label>
      <label>{{ t('assistant') }}<select v-model="inboxAssistant"><option value="">{{ t('all') }}</option><option v-for="a in assistants" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
      <label>{{ t('status') }}<select v-model="inboxStatus"><option value="">{{ t('all') }}</option><option v-for="s in ['open', 'active', 'awaiting_customer', 'awaiting_agent', 'awaiting_approval', 'escalated', 'resolved', 'closed']" :key="s" :value="s">{{ t(s==='open'?'status_open':s) }}</option></select></label>
      <label>{{ t('conversationLanguage') }}<select v-model="inboxLocale"><option value="">{{ t('all') }}</option><option v-for="l in ['bg-BG', 'en-US']" :key="l" :value="l">{{ t(l) }}</option></select></label>
      <label>{{ t('conversationDate') }}<input v-model="inboxDate" type="date"></label>
    </article>
</details>
    <InboxQueue v-if="selectedConversation && canExecute" :conversation="selectedConversation" :user-id="data.user.id" @changed="run(refreshQueue)" />
    <article v-if="current && canExecute" class="controls">
      <button :disabled="busy || closed" @click="run(() => control('takeover'))">
{{ t('takeover') }}
</button>
      <button :disabled="busy || closed" @click="run(() => control('resume'))">
{{ t('resume') }}
</button>
      <button :disabled="busy" @click="run(() => control('close'))">
{{ t('closeConversation') }}
</button>
      <form v-if="paused && !closed" @submit.prevent="run(humanReply)">
<label>{{ t('humanReply') }}<textarea v-model="text" required maxlength="10000" /></label><button :disabled="busy">
{{ t('send') }}
</button>
</form>
    </article>
    <article v-if="paused">
<p>{{ t('human_requested') }}</p>
</article>
    <article v-if="canExecute">
<div class="controls">
<label>{{ t('assistant') }}<select v-model="assistantId"><option v-for="a in assistants" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><label>{{ t('conversationLanguage') }}<select v-model="conversationLanguage" :aria-label="t('conversationLanguage')"><option value="auto">{{ t('autoLanguage') }}</option><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><label>{{ t('channel') }}<select v-model="channel"><option v-for="c in channels" :key="c" :value="c">{{ t(c) }}</option></select></label><label>{{ t('selectContact') }}<select v-model="contactId"><option value="">{{ t('none') }}</option><option v-for="c in contacts" :key="c.id" :value="c.id">{{ c.name }}</option></select></label><button :disabled="busy" @click="run(createConversation)">
{{ t('newConversation') }}
</button>
</div>
</article>
    <div class="inbox-layout">
<aside>
<button v-for="c in visibleConversations" :key="c.id" :class="{ selected: current === c.id }" :aria-pressed="current === c.id" @click="run(() => openConversation(c.id))">
{{ c.contact?.name || c.id.slice(0, 8) }} · {{ t(c.channel) }} · {{ t(c.active_locale || 'bg-BG') }}
<small>{{ assistants.find(a => a.id === c.assistant_id)?.name }} · {{ t(c.assigned_agent || 'receptionist') }} · {{ t(c.status==='open'?'status_open':c.status) }}</small>
<small v-if="c.last_message_at">{{ date(c.last_message_at, tz) }}</small><small>{{ c.last_message }}</small>
</button>
<button v-if="nextInboxCursor != null" :disabled="busy" @click="run(() => reloadInbox(true))">
{{ t('loadMoreConversations') }}
</button>
<p v-if="!visibleConversations.length && !busy">
{{ t('empty') }}
</p>
</aside><article>
<h2>{{ t('history') }}</h2><div class="messages" aria-live="polite">
<div v-for="m in messages" :key="m.id" class="bubble" :class="m.direction">
<small>{{ t(messageSpeaker(m)) }} · {{ date(m.timestamp, tz) }} · {{ t(m.locale) }}</small><p>{{ m.content }}</p><span class="badge">{{ t(m.delivery_status || m.status) }}</span>
<p v-for="a in m.attachments" :key="a.storage_key">
{{ a.name }} · {{ number(a.size) }} · {{ t('quarantined') }}
</p>
<button v-if="m.delivery_status === 'draft' && canExecute" :disabled="busy" @click="run(() => approveDraft(m.id))">
{{ t('approveDraft') }}
</button>
</div><EmptyState v-if="!messages.length" :title="t('empty')" />
</div>
    <form v-if="canExecute && !paused && !closed" @submit.prevent="run(send)">
<fieldset :disabled="busy">
<label>{{ t('action') }}<select v-model="tool"><option value="">{{ t('none') }}</option><option v-for="name in inboxTools" :key="name" :value="name">{{ t(name) }}</option></select></label>
      <template v-if="['CheckAvailability', 'CreateAppointment', 'RescheduleAppointment'].includes(tool)">
<label>{{ t('date') }}<input v-model="startsAt" type="text" :placeholder="t('dateExample')" required></label><p>{{ t('localDateHelp') }} {{ tz }}</p><label>{{ t('duration') }}<input v-model.number="duration" type="number" min="5" max="480" required></label>
</template>
      <label v-if="['CreateAppointment', 'RescheduleAppointment'].includes(tool)">{{ t('contactName') }}<input v-model="contactName" required></label>
      <label v-if="['CancelAppointment', 'RescheduleAppointment'].includes(tool)">{{ t('selectAppointment') }}<select v-model="appointmentId" required><option value="">{{ t('selectAppointment') }}</option><option v-for="a in appointments.filter(x => x.status !== 'cancelled')" :key="a.id" :value="a.id">{{ a.contact_name }} · {{ date(a.starts_at, tz) }}</option></select></label>
      <template v-if="tool === 'SendMessage'">
<label>{{ t('channel') }}<select v-model="sendChannel"><option v-for="c in channels" :key="c" :value="c">{{ t(c) }}</option></select></label><label>{{ t('recipient') }}<input v-model="recipient" required></label>
</template>
      <template v-if="tool === 'CreateFollowUpTask'">
<label>{{ t('task') }}<input v-model="title" required></label><label>{{ t('dueAt') }}<input v-model="dueAt" type="text" :placeholder="t('dateExample')" required></label>
</template>
      <label v-if="tool === 'EscalateToHuman'">{{ t('reason') }}<input v-model="reason" required></label><label>{{ t('message') }}<textarea v-model="text" :required="!tool || tool === 'SendMessage'" maxlength="10000" /></label>
      <label v-if="channel === 'web_chat' && !tool">{{ t('attachment') }}<input type="file" accept=".txt,.csv,.pdf,.png,.jpg,.jpeg,.ics" @change="run(() => attach($event))"></label><button>{{ t('send') }}</button>
</fieldset>
</form>
</article>
</div>
    <article v-for="a in pending" :key="a.id" class="approval">
<h2>{{ t(a.tool) }}</h2><p>{{ t('confirmation') }}</p><dl>
<template v-for="(value, key) in a.arguments" :key="key">
<dt>{{ t(argumentLabels[String(key)] || String(key)) }}</dt><dd>{{ formatArgument(String(key), value) }}</dd>
</template>
</dl><button v-if="canExecute" :disabled="busy" @click="run(() => approve(a.id))">
{{ t('confirm') }}
</button>
</article>
  </template>
  <ConversationDebugger v-if="page === 'inbox' && current && canExecute" :conversation-id="current" :timezone="tz" />
  <template v-if="page === 'appointments'">
<RouterLink v-if="route.query.conversation" to="/appointments">
{{ t('showAllAppointments') }}
</RouterLink>
<article>
<h2>{{ t('appointments') }}</h2><div class="table-wrap">
<table>
<thead><tr><th>{{ t('contactName') }}</th><th>{{ t('date') }}</th><th>{{ t('status') }}</th></tr></thead><tbody>
<tr v-for="a in appointments.filter(item => !route.query.conversation || item.conversation_id === route.query.conversation)" :key="a.id">
<td>
{{ a.contact_name }}<br><RouterLink v-if="a.conversation_id" :to="{path:'/inbox',query:{conversation:a.conversation_id}}">
{{ t('openConversation') }}
</RouterLink>
</td><td>{{ date(a.starts_at, tz) }}</td><td>{{ t(a.status) }}</td>
</tr>
</tbody>
</table>
</div><EmptyState v-if="!appointments.length" :title="t('empty')" />
</article><article>
<h2>{{ t('followUps') }}</h2><p v-for="f in followUps" :key="f.id">
{{ f.title }} · {{ t(f.status) }}
</p>
</article>
</template>
  <template v-if="page === 'calls'">
<article>
<p>{{ t('speechNotice') }}</p><label>{{ t('callLanguage') }}<select v-model="locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><label>{{ t('assistant') }}<select v-model="assistantId"><option v-for="a in assistants" :key="a.id" :value="a.id">{{ a.name }}</option></select></label><button v-if="canExecute && assistants.find(a => a.id === assistantId)?.voice_settings?.telephony_provider === 'mock'" :disabled="busy" @click="run(startCall)">
{{ t('startCall') }}
</button><label>{{ t('transcript') }}<textarea v-model="text" /></label>
</article><article v-for="c in calls" :key="c.id">
<h2>{{ t(c.status==='open'?'status_open':c.status) }} · {{ t(c.voice_locale) }}</h2><span class="badge">{{ t(c.state) }}</span><p>{{ c.last_response }}</p><div class="controls">
<p>{{ t('assistant') }}: {{ assistants.find(a => a.id === c.assistant_id)?.name }} · {{ t('id') }}: {{ c.id }}</p>
<p v-if="c.error_code">
{{ t('error') }}: {{ t(c.error_code) }}
</p>
<button v-if="canExecute" :disabled="busy" @click="run(async () => { diagnosticConversation = c.conversation_id; if(canConfigure) await showCallActivity(c.id); })">
{{ t('callActivity') }}
</button>
<button v-if="c.state === 'MOCK' && c.status === 'listening' && canExecute && streamCall !== c.id" :disabled="busy" @click="run(() => openVoice(c))">
{{ t('connectAudio') }}
</button>
<template v-if="streamCall === c.id && streamReady">
<button :disabled="!text" @click="sendVoice">
{{ t('sendAudioFixture') }}
</button><button @click="stream?.send(JSON.stringify({ event: 'barge_in' }))">
{{ t('barge_in') }}
</button><button @click="stream?.send(JSON.stringify({ event: 'stop' }))">
{{ t('terminate') }}
</button>
</template>
<button v-for="action in c.status === 'listening' ? ['speak', 'transcript', 'language', 'transfer', 'terminate'] : c.status === 'speaking' ? ['barge_in', 'finish_speaking', 'language', 'transfer', 'terminate'] : []" :key="action" :disabled="busy || !canExecute" @click="run(() => callAction(c, action))">
{{ t(action === 'language' ? 'languageSwitch' : action) }}
</button>
</div>
</article>
<article v-if="callActivity">
  <h2>{{ t('callActivity') }} · {{ callActivity.call.id }}</h2>
  <p>{{ t('agentExecutions') }}: {{ number(callActivity.agents.length) }} · {{ t('toolExecutions') }}: {{ number(callActivity.tools.length) }}</p>
  <p v-for="execution in callActivity.tools" :key="execution.id">
{{ t(execution.tool) }} · {{ t(execution.outcome.code) }}
</p>
  <p v-for="appointment in callActivity.appointments" :key="appointment.id">
{{ t('appointments') }} · {{ appointment.id }} · {{ t(appointment.status) }} · {{ date(appointment.starts_at, tz) }}
</p>
  <p v-for="entry in callActivity.usage.filter((u: any) => u.kind === 'llm_inference')" :key="entry.id">
{{ t('llmTokens') }}: {{ entry.usage_reported ? number(entry.llm_input_tokens + entry.llm_output_tokens) : t('tokenUsageUnavailable') }}
</p>
</article>
<ConversationDebugger v-if="diagnosticConversation && canExecute" :conversation-id="diagnosticConversation" :timezone="tz" />
</template>
  <template v-if="page === 'channels' || page === 'integrations'">
<div class="cards">
<article v-for="provider in data.providers" :key="provider.kind">
<h2>{{ t(provider.kind) }}</h2><span class="badge">{{ t(providerStatus(provider)) }}</span><p>{{ t('bg-BG') }} / {{ t('en-US') }}</p><p>{{ t('providerStatusScope') }}</p>
</article>
</div><MessagingConnections :assistants="assistants" :connections="connections" :allowed="canConfigure" @refresh="run(load)" />
</template>
  <template v-if="page === 'settings'">
    <article v-if="canConfigure">
      <h2>{{ t('memberships') }}</h2>
      <form @submit.prevent="run(addUser)">
<label>{{ t('subject') }}<input v-model="newUser.subject" required></label><label>{{ t('role') }}<select v-model="newUser.role"><option v-for="role in ['admin', 'operator', 'viewer']" :key="role" :value="role">{{ t(role) }}</option></select></label><button :disabled="busy">
{{ t('save') }}
</button>
</form>
      <p v-for="u in users" :key="u.id">
{{ u.subject }} · {{ t(u.role) }}
</p>
    </article>
    <article v-if="canConfigure">
<h2>{{ t('templates') }}</h2><form v-for="template in templates" :key="template.id" @submit.prevent="run(() => saveTemplate(template))">
<label>{{ t(template.locale) }} · {{ t(template.key === 'appointment_created' ? 'CreateAppointment' : template.key === 'subject' ? 'subjectTemplate' : template.key) }}<textarea v-model="template.body" required /></label><button :disabled="busy">
{{ t('save') }}
</button>
</form>
</article>
    <article v-if="canConfigure">
<h2>{{ t('reminders') }}</h2><button :disabled="busy" @click="run(async () => { await request('/api/jobs/run', 'POST', { confirmed: true }); await load(); notice = t('saved'); })">
{{ t('runReminders') }}
</button><p v-for="job in jobs" :key="job.id">
{{ date(job.due_at, tz) }} · {{ t(job.status) }}
</p>
</article>
<article>
<h2>{{ t('tenantSettings') }}</h2><form @submit.prevent="run(saveSettings)">
<fieldset :disabled="!canConfigure || busy">
<label>{{ t('defaultLocale') }}<select v-model="settings.default_locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><label>{{ t('timezone') }}<input v-model="settings.timezone" required></label><label>{{ t('usageLimit') }}<input v-model.number="settings.usage_limit" type="number" min="1" required></label><label>{{ t('retentionDays') }}<input v-model.number="settings.retention_days" type="number" min="1" required></label><label class="check"><input v-model="settings.recording_enabled" type="checkbox">{{ t('recording') }}</label><label class="check"><input v-model="settings.transcripts_enabled" type="checkbox">{{ t('transcripts') }}</label><label class="check"><input v-model="settings.notice_acknowledged" type="checkbox">{{ t('notice') }}</label><button>{{ t('save') }}</button>
</fieldset>
</form><button v-if="canConfigure" :disabled="busy" @click="run(async () => { await request('/api/retention/redact', 'POST', { confirmed: true }); notice = t('saved'); })">
{{ t('retention') }}
</button>
</article>
    <article>
<h2>{{ t('contacts') }}</h2><form v-if="canExecute" @submit.prevent="run(addContact)">
<label>{{ t('name') }}<input v-model="newContact.name" required></label><label>{{ t('address') }}<input v-model="newContact.address" required></label><label>{{ t('conversationLanguage') }}<select v-model="newContact.preferred_locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><label class="check"><input v-model="newContact.sms_opt_out" type="checkbox">{{ t('optOut') }}</label><button :disabled="busy">
{{ t('addContact') }}
</button>
</form><p v-for="c in contacts" :key="c.id">
{{ c.name }} · {{ t(c.preferred_locale) }} · {{ c.address }}
</p>
</article><article v-if="canConfigure">
<h2>{{ t('audit') }}</h2><p v-for="a in audit" :key="a.id">
{{ date(a.timestamp, tz) }} · {{ t(a.action.startsWith('tool:') ? a.action.slice(5) : a.action) }} · {{ t(a.status) }}
</p>
</article>
  </template>
</template>
