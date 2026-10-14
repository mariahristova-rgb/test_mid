<script setup lang="ts">
import { validateSetupForm } from '../services/setupValidation.mjs';
import { scheduleLocal, scheduleInstant } from '../services/businessSchedule.mjs';
import { computed, onMounted, ref, watch, nextTick, onUnmounted } from 'vue';
import { useRoute, useRouter, onBeforeRouteLeave } from 'vue-router';
import { request, ApiError } from '../services/api';
import { t, uiLocale, date, number } from '../services/i18n';
const route = useRoute(), router = useRouter();
const access = ref<any>({}), drafts = ref<any[]>([]), assistants = ref<any[]>([]), draft = ref<any>(null), readiness = ref<any>(null), receipts = ref<any[]>([]);
const busy = ref(false), error = ref(''), notice = ref(''), confirmed = ref(false), abandon = ref(false), selected = ref('');
const baseline = ref('');
const setupForm = ref<HTMLFormElement | null>(null);
const errorPanel = ref<HTMLElement | null>(null);
function validateForm() {
  return validateSetupForm(setupForm.value, () => { error.value = t('setupValidationHelp'); });
}
const recovery = ref('');
const reloadConfirmed = ref(false);
const locale = ref<'bg-BG'|'en-US'>('bg-BG'), scenario = ref('booking');
const steps = ['useCaseStep','businessStep','languageStep','toolsStep','channelsStep','testingStep','reviewStep'];
const scenarios = ['booking','short_confirmation','rejection','ambiguous','occupied','language_switch','handoff','interruption','faq','greeting','reschedule','cancellation','out_of_hours','closed_day','unsupported','provider_failure','provider_uncertain'];
const testing = computed(() => route.meta.page === 'testing');
const canConfigure = computed(() => access.value.user?.role === 'admin');
const canExecute = computed(() => ['admin','operator'].includes(access.value.user?.role));
const editable = computed(() => draft.value?.status === 'draft' && canConfigure.value);
const dirty = computed(() => draft.value && JSON.stringify(draft.value) !== baseline.value);
const latest = computed(() => receipts.value.at(-1));
function runValidated(action: () => Promise<unknown>) { if(validateForm()) void run(action); }
async function run(action: () => Promise<unknown>) {
  if (busy.value) return; busy.value = true; error.value = ''; notice.value = ''; recovery.value = '';
  try { await action(); } catch(e) {
    if(e instanceof ApiError && e.code === 'test_worker_busy') {error.value=t('test_worker_busy'); recovery.value='busy';}
    else if(e instanceof ApiError && e.status === 409) {error.value=t('draftConflictHelp'); recovery.value='revision';}
    else error.value = e instanceof Error && e.message ? e.message : t('error');
  }
  finally { busy.value = false; if(error.value) { await nextTick(); errorPanel.value?.focus(); } }
}
function payload() {
  return { revision: draft.value.revision || 0, assistant_id: draft.value.target_assistant_id || null,
    use_case: draft.value.use_case, step: draft.value.step, config: draft.value.config, business: draft.value.business };
}
async function load() {
  access.value = await request('/api/bootstrap'); assistants.value = await request('/api/assistants');
  if (!canExecute.value) return;
  drafts.value = await request('/api/ux/drafts');
  if (route.query.draft) await open(String(route.query.draft));
  else if(route.query.assistant && canConfigure.value) newDraft(String(route.query.assistant));
  if(scenarios.includes(String(route.query.scenario))) scenario.value = String(route.query.scenario);
}
async function open(id: string) {
  const found = drafts.value.find(d => d.id === id);
  if (!found) throw new Error(t('not_found'));
  draft.value = JSON.parse(JSON.stringify(found));
  draft.value.business = { description:'',contact_email:'',contact_phone:'',service_price:'',price_currency:'EUR',holidays:found.calendar_base?.holidays || [],unavailable_periods:found.calendar_base?.unavailable_periods || [],...draft.value.business };
  baseline.value = JSON.stringify(draft.value); confirmed.value = false;
  selected.value = id;
  await evidence();
}
async function evidence() {
  if (!draft.value?.id) return;
  [readiness.value, receipts.value] = await Promise.all([request(`/api/ux/drafts/${draft.value.id}/readiness`),request(`/api/ux/drafts/${draft.value.id}/tests`)]);
}
async function reloadSaved() { if(dirty.value && !reloadConfirmed.value) { error.value=t('reloadDiscardHelp'); return; } reloadConfirmed.value=false; const identity = draft.value.id; drafts.value = await request('/api/ux/drafts'); await open(identity); }
function newDraft(id?: string) {
  const original = assistants.value.find(a => a.id === id);
  const initial = original || assistants.value[0];
  if (!initial) { error.value = t('setupNeedsAssistant'); return; }
  const source = JSON.parse(JSON.stringify(initial));
  delete source.id; delete source.tenant_id;
  if (!original) {
    source.name = t('newAssistantName'); source.enabled_channels = ['web_chat']; source.llm_provider = 'mock'; source.voice_provider = 'mock';
    source.allowed_tools = ['CheckAvailability','CreateAppointment','EscalateToHuman'];
    source.instructions = t('template_receptionist');
    source.voice_settings = { ...source.voice_settings, telephony_provider:'mock', stt_provider:'mock', tts_provider:'mock', voices:{'bg-BG':'mock-bg','en-US':'mock-en'},recording:false,transcript_storage:false };
  }
  const tenant = access.value.tenant, policy = tenant.calendar_policy || {};
  draft.value = { revision:0, status:'draft', target_assistant_id:id || null, use_case:'receptionist', step:0, config:source,
    business:{name:tenant.name,website:tenant.website || '',industry:tenant.industry || '',timezone:tenant.timezone, weekdays:policy.weekdays || [0,1,2,3,4],opens:policy.opens || '09:00',closes:policy.closes || '18:00',service:policy.service_id || t('consultationService'),duration_minutes:source.booking_duration_minutes,
      description:tenant.description || '',contact_email:tenant.contact_email || '',contact_phone:tenant.contact_phone || '',service_price:tenant.service_price || '',price_currency:tenant.price_currency || 'EUR',holidays:JSON.parse(JSON.stringify(policy.holidays || [])),unavailable_periods:JSON.parse(JSON.stringify(policy.unavailable_periods || []))} };
  baseline.value = ''; readiness.value = null; receipts.value = []; confirmed.value = false;
}
async function save() {
  const saved = await request(draft.value.id ? `/api/ux/drafts/${draft.value.id}` : '/api/ux/drafts',draft.value.id ? 'PUT' : 'POST',payload());
  reloadConfirmed.value=false; draft.value = saved; baseline.value = JSON.stringify(saved); selected.value = saved.id;
  drafts.value = await request('/api/ux/drafts'); await evidence(); notice.value = t('saved');
}
async function move(step: number) {
  const previous = draft.value.step;
  draft.value.step = step;
  try { await save(); } catch(e) { draft.value.step = previous; throw e; } await nextTick(); document.getElementById('setup-step')?.focus();
}
async function testOne(chosen = scenario.value, language = locale.value) {
  if (dirty.value && canConfigure.value) await save();
  if (!draft.value?.id) throw new Error(t('saveBeforeTesting'));
  await request(`/api/ux/drafts/${draft.value.id}/tests`,'POST',{ revision:draft.value.revision,scenario:chosen,locale:language });
  await evidence();
}
async function suite() {
  if(dirty.value && canConfigure.value) await save();
  const required = [...new Set<string>((readiness.value?.required_tests || []).map((row:any) => row.scenario))];
  for (const language of ['bg-BG','en-US'] as const) for (const chosen of required) await testOne(chosen,language);
}
function addFaq() { draft.value.config.faq_entries.push({question_bg:'',question_en:'',answer_bg:'',answer_en:''}); }
function setPeriod(period:any,key:string,value:string) {
  try { period[key]=scheduleInstant(value,draft.value.business.timezone);error.value=''; }
  catch { period[key]='';error.value=t('p21InvalidLocalTime'); }
}
async function publish() {
  await request(`/api/ux/drafts/${draft.value.id}/publish`,'POST',{revision:draft.value.revision,confirmed:confirmed.value});
  abandon.value = true; await router.push('/assistants');
}
async function cancel() {
  await request(`/api/ux/drafts/${draft.value.id}/cancel`,'POST',{revision:draft.value.revision,confirmed:confirmed.value});
  abandon.value = true; draft.value = null; await load();
}
onBeforeRouteLeave(() => !dirty.value || abandon.value);
function beforeUnload(event: BeforeUnloadEvent) { if(dirty.value) {event.preventDefault(); event.returnValue='';} }
onMounted(() => { void run(load); window.addEventListener('beforeunload',beforeUnload); });
onUnmounted(() => window.removeEventListener('beforeunload',beforeUnload));
watch(() => route.meta.page, () => { if(!draft.value) void run(load); });
</script>
<template>
  <div class="page-heading">
<h1>{{ t(testing ? 'testing' : 'setup') }}</h1><RouterLink to="/assistants">
{{ t('assistants') }}
</RouterLink>
</div>
  <p class="banner">
{{ t('isolatedStudioNotice') }}
</p>
  <p v-if="busy" role="status">
{{ t('busy') }}
</p><p
v-if="error"
id="setup-error"
ref="errorPanel"
class="error"
role="alert"
tabindex="-1"
>
{{ error }}
</p><p v-if="notice" role="status">
{{ notice }}
</p>
  <div v-if="recovery" class="controls">
<label v-if="recovery === 'revision' && dirty" class="check"><input v-model="reloadConfirmed" type="checkbox">{{ t('reloadDiscardHelp') }}</label>
<button :disabled="busy" @click="run(evidence)">
{{ t('refreshTestResults') }}
</button><button v-if="recovery === 'revision'" :disabled="busy || (!!dirty && !reloadConfirmed)" @click="run(reloadSaved)">
{{ t('reloadSavedDraft') }}
</button>
</div>
  <p v-if="!canExecute && access.user" role="status">
{{ t('forbidden') }}
</p>
  <article v-if="canExecute">
<h2>{{ t('resumeSetup') }}</h2>
    <label>{{ t('savedDraft') }}<select v-model="selected" :disabled="busy || !!dirty"><option value="">{{ t('selectDraft') }}</option><option v-for="item in drafts" :key="item.id" :value="item.id">{{ item.config.name }} · {{ t(item.status) }}</option></select></label>
    <button :disabled="busy || !selected || !!dirty" @click="run(() => open(selected))">
{{ t('open') }}
</button>
    <button v-if="canConfigure" :disabled="busy || !!dirty" @click="newDraft()">
{{ t('newAssistantName') }}
</button>
    <button v-if="dirty" :disabled="busy" @click="abandon = true; draft = null; baseline = ''; abandon = false">
{{ t('discardLocalChanges') }}
</button>
  </article>
  <template v-if="draft">
    <p role="status">
{{ t(draft.status) }} · {{ t('revision') }} {{ number(draft.revision) }} · {{ t(draft.config.llm_provider === 'mock' ? 'MOCK_ONLY' : 'CONFIGURED') }}
</p>
    <p v-if="dirty" class="banner" role="status">
{{ t('unsavedChanges') }}
</p>
    <article v-if="!testing">
      <p role="status">
{{ t('setupProgress') }} {{ number(draft.step + 1) }} / {{ number(steps.length) }} · {{ t('setupProgressHelp') }}
</p>
      <ol class="steps">
<li v-for="(key,index) in steps" :key="key" :aria-current="draft.step === index ? 'step' : undefined">
{{ t(key) }}
</li>
</ol>
      <h2 id="setup-step" tabindex="-1">
{{ t(steps[draft.step]) }}
</h2>
      <form ref="setupForm" novalidate :aria-describedby="error ? 'setup-error' : undefined" @submit.prevent="runValidated(() => move(Math.min(6,draft.step + 1)))">
<fieldset :disabled="busy || !editable">
<legend class="visually-hidden">
{{ t(steps[draft.step]) }}
</legend>
        <template v-if="draft.step === 0">
<label>{{ t('useCaseStep') }}<select v-model="draft.use_case" @change="draft.config.instructions = t('template_' + draft.use_case)"><option v-for="value in ['receptionist','support','sales','general']" :key="value" :value="value">{{ t('useCase_' + value) }}</option></select></label>
          <label>{{ t('name') }}<input v-model="draft.config.name" required maxlength="120"></label>
          <label>{{ t('instructions') }}<textarea v-model="draft.config.instructions" maxlength="8000" /></label>
          <details>
<summary>{{ t('approvedFaqs') }}</summary><p>{{ t('faqApprovalHelp') }}</p><fieldset v-for="(faq,index) in draft.config.faq_entries" :key="index">
<legend>{{ t('faqEntry') }} {{ number(Number(index)+1) }}</legend><label>{{ t('questionBg') }}<input v-model="faq.question_bg" required maxlength="500"></label><label>{{ t('answerBg') }}<textarea v-model="faq.answer_bg" required maxlength="2000" /></label><label>{{ t('questionEn') }}<input v-model="faq.question_en" required maxlength="500"></label><label>{{ t('answerEn') }}<textarea v-model="faq.answer_en" required maxlength="2000" /></label><button type="button" @click="draft.config.faq_entries.splice(index,1)">
{{ t('removeFaq') }}
</button>
</fieldset><button type="button" :disabled="draft.config.faq_entries.length >= 20" @click="addFaq">
{{ t('addFaq') }}
</button>
</details>
          <p>{{ t('useCaseHelp') }}</p><p v-if="!draft.config.faq_entries.length">
{{ t('faqOptionalEmpty') }}
</p>
        </template>
        <template v-if="draft.step === 1">
<h3>{{ t('businessDetailsHelp') }}</h3>
          <label>{{ t('organizationName') }}<input v-model="draft.business.name" required maxlength="120"></label>
          <label>{{ t('businessWebsite') }}<input v-model="draft.business.website" type="url" maxlength="500"></label><label>{{ t('businessIndustry') }}<input v-model="draft.business.industry" maxlength="120"></label>
          <label>{{ t('p21Description') }}<textarea v-model="draft.business.description" maxlength="1000" /></label>
          <label>{{ t('p21ContactEmail') }}<input v-model="draft.business.contact_email" type="email" maxlength="250"></label>
          <label>{{ t('p21ContactPhone') }}<input v-model="draft.business.contact_phone" type="tel" maxlength="50"></label>
          <h3>{{ t('scheduleSetupHelp') }}</h3>
          <label>{{ t('timezone') }}<input v-model="draft.business.timezone" required></label>
          <fieldset>
<legend>{{ t('workingDays') }}</legend><div class="checks">
<label v-for="day in [0,1,2,3,4,5,6]" :key="day"><input v-model="draft.business.weekdays" type="checkbox" :value="day">{{ t('weekday_' + day) }}</label>
</div>
</fieldset>
          <label>{{ t('opens') }}<input v-model="draft.business.opens" type="time" required></label><label>{{ t('closes') }}<input v-model="draft.business.closes" type="time" required></label>
          <h3>{{ t('serviceSetupHelp') }}</h3>
          <label>{{ t('serviceName') }}<input v-model="draft.business.service" required maxlength="120"></label>
          <label>{{ t('p21ServicePrice') }}<input v-model="draft.business.service_price" inputmode="decimal" maxlength="12"></label>
          <label>{{ t('p21Currency') }}<select v-model="draft.business.price_currency"><option v-for="code in ['EUR','BGN','USD']" :key="code" :value="code">{{ code }}</option></select></label><p>{{ t('p21PriceHelp') }}</p>
          <fieldset>
<legend>{{ t('p21Holidays') }}</legend><label v-for="(_,index) in draft.business.holidays" :key="index">{{ t('p21ClosedDate') }}<input v-model="draft.business.holidays[index]" type="date" required><button type="button" @click="draft.business.holidays.splice(index,1)">{{ t('p21Remove') }}</button></label><button type="button" :disabled="draft.business.holidays.length>=100" @click="draft.business.holidays.push('')">
{{ t('p21AddHoliday') }}
</button>
</fieldset>
          <fieldset>
<legend>{{ t('p21Unavailable') }}</legend><p>{{ t('p21IntervalHelp') }} {{ draft.business.timezone }}</p><label v-for="(period,index) in draft.business.unavailable_periods" :key="index">{{ t('p21StartsAt') }}<input :value="scheduleLocal(period.starts_at,draft.business.timezone)" type="datetime-local" required @input="setPeriod(period,'starts_at',($event.target as HTMLInputElement).value)"><span>{{ t('p21EndsAt') }}</span><input :value="scheduleLocal(period.ends_at,draft.business.timezone)" type="datetime-local" required @input="setPeriod(period,'ends_at',($event.target as HTMLInputElement).value)"><button type="button" @click="draft.business.unavailable_periods.splice(index,1)">{{ t('p21Remove') }}</button></label><button type="button" :disabled="draft.business.unavailable_periods.length>=100" @click="draft.business.unavailable_periods.push({starts_at:'',ends_at:''})">
{{ t('p21AddPeriod') }}
</button>
</fieldset><p>{{ t('p21ScheduleScope') }}</p>
          <label>{{ t('duration') }}<input
v-model.number="draft.business.duration_minutes"
type="number"
min="5"
max="480"
required
@input="draft.config.booking_duration_minutes = draft.business.duration_minutes"
></label>
        </template>
        <template v-if="draft.step === 2">
          <p>{{ t('bothLocalesRequired') }}</p>
          <label>{{ t('language') }}<select v-model="uiLocale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label>
          <label>{{ t('conversationLanguage') }}<select v-model="draft.config.default_locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label>
          <label>{{ t('callLanguage') }}<select v-model="draft.config.voice_settings.locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label>
          <p>{{ t('providerPreserved') }}</p>
        </template>
        <template v-if="draft.step === 3">
          <p>{{ t('twoAgentHelp') }}</p><RouterLink to="/agents">
{{ t('agents') }}
</RouterLink>
          <fieldset><legend>{{ t('tools') }}</legend><label v-for="item in access.tools" :key="item.name" class="check"><input v-model="draft.config.allowed_tools" type="checkbox" :value="item.name">{{ t(item.name) }}</label></fieldset>
          <p>{{ t('permissionIntersection') }}</p><p>{{ t('escalationSetupHelp') }}</p>
        </template>
        <template v-if="draft.step === 4">
          <fieldset><legend>{{ t('channels') }}</legend><label v-for="value in ['web_chat','voice','email','whatsapp','sms']" :key="value" class="check"><input v-model="draft.config.enabled_channels" type="checkbox" :value="value">{{ t(value) }}</label></fieldset>
          <p>{{ t('external_activation_blocked') }}</p>
        </template>
        <template v-if="draft.step === 5">
<p>{{ t('testBeforePublish') }}</p>
</template>
        <template v-if="draft.step === 6">
<p>{{ t('readinessReview') }}</p>
</template>
        <div class="controls">
<button v-if="draft.step > 0" type="button" @click="runValidated(() => move(draft.step - 1))">
{{ t('back') }}
</button><button type="button" @click="runValidated(save)">
{{ t('saveDraft') }}
</button><button v-if="draft.step < 6">
{{ t('continueSetup') }}
</button>
</div>
      </fieldset>
</form>
    </article>
    <article v-if="draft.status === 'draft' && (testing || draft.id)">
<h2>{{ t('testing') }}</h2><p>{{ t('previewSavedHelp') }}</p><p>{{ t('previewExpectedHelp') }}</p><p v-if="['reschedule','cancellation'].includes(scenario)">
{{ t('previewManagementScope') }}
</p><p v-if="['provider_failure','provider_uncertain'].includes(scenario)">
{{ t('previewFaultScope') }}
</p>
      <label>{{ t('conversationLanguage') }}<select v-model="locale"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label>
      <label>{{ t('scenario') }}<select v-model="scenario"><option v-for="key in scenarios" :key="key" :value="key">{{ t('scenario_' + key) }}</option></select></label>
      <div class="controls">
<button :disabled="busy" @click="runValidated(() => testOne())">
{{ t('runScenario') }}
</button><button :disabled="busy" @click="runValidated(suite)">
{{ t('runRequiredTests') }}
</button>
</div>
    </article>
    <article v-if="latest" aria-live="polite">
<h2>{{ t(latest.verdict) }} · {{ t('scenario_' + latest.scenario) }}</h2>
      <p>
{{ t('simulatedPreview') }} · {{ date(latest.timestamp,latest.timezone || draft.business.timezone) }} · {{ t('revision') }} {{ number(latest.revision) }} · {{ latest.config_hash === draft.config_hash && !dirty ? t('previewCurrent') : t('previewStale') }}
</p><p>
{{ t('duration') }}: {{ number(latest.duration_ms) }} {{ t('milliseconds') }} · {{ t(latest.locale) }} · {{ t('MOCK_ONLY') }}
</p>
        <p v-if="latest.reference_at">
{{ t('syntheticClock') }}: {{ date(latest.reference_at,latest.timezone) }} · {{ latest.timezone }}
</p>
      <p>{{ t('expectedBookings') }}: {{ number(latest.expected_booking_count || 0) }} · {{ t('observedBookings') }}: {{ number(latest.booking_count) }}</p>
      <p>{{ t(['faq'].includes(latest.scenario) ? 'previewFaqConfig' : ['booking','short_confirmation','rejection','ambiguous','occupied','language_switch','reschedule','cancellation','out_of_hours','closed_day','provider_failure','provider_uncertain'].includes(latest.scenario) ? 'previewBookingConfig' : 'previewBehaviorConfig') }}</p>
      <p v-if="latest.verdict !== 'PASS'">
{{ t('previewRecoveryHelp') }}
</p>
      <p v-if="latest.code !== 'completed'">
{{ t(latest.code) }}
</p>
      <div class="diagnostic-grid">
<section>
<h3>{{ t('history') }}</h3><div v-for="(turn,index) in latest.turns" :key="index" class="bubble">
<p>{{ turn.input }}</p><p>{{ turn.response }}</p><small>{{ t(turn.locale) }} · {{ t(turn.booking_status === 'unknown' ? 'previewUnknownStatus' : turn.booking_status === 'failed' ? 'previewFailedStatus' : turn.booking_status || 'notRecorded') }} · {{ number(turn.duration_ms) }} {{ t('milliseconds') }}</small>
</div>
</section>
      <section>
<h3>{{ t('agentExecutions') }}</h3><p v-for="(agent,index) in latest.agents" :key="index">
{{ t(agent.source) }} → {{ t(agent.target) }} · {{ t(agent.locale) }}
</p><h3>{{ t('toolExecutions') }}</h3><p v-for="(tool,index) in latest.tools" :key="index">
{{ t(tool.tool) }} · {{ t(tool.code) }}
</p>
</section>
</div>
    </article>
    <article v-if="readiness">
<RouterLink v-if="draft.status === 'published'" to="/widgets">
{{ t('widgets') }}
</RouterLink>
<h2>{{ t('readinessReview') }}</h2><p role="status">
{{ t(draft.status === 'published' ? 'setupActivated' : readiness.required_tests?.length && readiness.required_tests.every((item:any) => item.verdict === 'PASS') && !dirty ? 'setupTested' : 'setupDraft') }}
</p><p>{{ t('voice_acceptance_blocked') }}</p>
      <ul>
<li v-for="key in readiness.reasons" :key="key">
{{ t(key) }}
</li>
</ul>
      <p v-for="item in readiness.channels" :key="item.channel">
{{ t(item.channel) }} · {{ t(item.status) }}
</p>
      <p v-if="dirty" class="banner" role="status">
{{ t('previewStale') }}
</p>
      <p v-for="item in readiness.required_tests" :key="item.scenario + item.locale">
{{ t('scenario_' + item.scenario) }} · {{ t(item.locale) }} · {{ dirty ? t('previewStale') : t(item.verdict) }}
</p>
      <template v-if="editable">
<p class="banner">
{{ t('sharedBusinessWarning') }}
</p><label class="check"><input v-model="confirmed" type="checkbox">{{ t('confirmConfigurationAction') }}</label>
      <button :disabled="busy || !!dirty || !confirmed || !readiness.can_publish" @click="run(publish)">
{{ t('publishWebChat') }}
</button>
      <button v-if="draft.id" :disabled="busy || !confirmed" @click="run(cancel)">
{{ t('cancelDraft') }}
</button>
</template>
    </article>
    <details v-if="receipts.length">
<summary>{{ t('testHistory') }}</summary><p v-for="item in receipts" :key="item.id">
{{ date(item.timestamp,draft.business.timezone) }} · {{ t('scenario_' + item.scenario) }} · {{ t(item.locale) }} · {{ dirty ? t('previewStale') : t(item.verdict) }} · {{ t('revision') }} {{ number(item.revision) }}
</p>
</details>
  </template>
</template>
