<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { request, tenantId } from '../services/api';
import { t, uiLocale, date, number } from '../services/i18n';
import { formatMinor } from '../services/money.mjs';
import EmptyState from '../components/EmptyState.vue';
const route = useRoute(), router = useRouter();
const page = computed(() => String(route.meta.page));
const access = ref<any>({}), state = ref<any>({}), plans = ref<any[]>([]), credentials = ref<any[]>([]), tenants = ref<any[]>([]);
const busy = ref(false), error = ref(''), notice = ref(''), token = ref(''), selectedPlan = ref('sandbox'), interval = ref('monthly');
const registration = ref({ name: '', email: '', default_locale: uiLocale.value, timezone: 'Europe/Sofia', plan_id: 'sandbox', interval: 'monthly' });
const tenantSelection = ref(tenantId.value), credentialName = ref(''), credentialValue = ref('');
const eventId = crypto.randomUUID();
const canConfigure = computed(() => access.value.role === 'admin');
const timezone = computed(() => access.value.timezone || registration.value.timezone);
function money(value: string | number, currency: string) { return formatMinor(value, currency, uiLocale.value); }
async function run(action: () => Promise<unknown>) {
  busy.value = true; error.value = ''; notice.value = '';
  try { await action(); } catch (e) { error.value = e instanceof Error ? e.message : t('error'); }
  finally { busy.value = false; }
}
async function load() {
  plans.value = await request('/api/saas/plans');
  try { access.value = await request('/api/saas/access'); } catch { access.value = {}; }
  if (page.value === 'onboarding' && canConfigure.value) state.value = await request('/api/saas/onboarding');
  if (page.value === 'billing' && canConfigure.value) state.value = await request('/api/billing');
  if (page.value === 'usage') state.value = await request('/api/usage');
  if (page.value === 'operations' && ['admin', 'operator'].includes(access.value.role)) {
    state.value = await request('/api/operations');
    if (canConfigure.value) credentials.value = await request('/api/credentials');
  }
  if (page.value === 'administration') tenants.value = await request('/api/platform/tenants');
  if (plans.value.length && !plans.value.some(p => p.id === selectedPlan.value)) selectedPlan.value = plans.value[0].id;
  if (page.value === 'onboarding' && state.value.plan_id) selectedPlan.value = state.value.plan_id;
  if (page.value === 'billing' && state.value.subscription?.plan_id) { selectedPlan.value = state.value.subscription.plan_id; interval.value = state.value.subscription.interval; }
  registration.value.plan_id = selectedPlan.value;
}
onMounted(() => run(load));
watch(page, () => { state.value = {}; void run(load); });
async function register() {
  const result = await request('/api/saas/register', 'POST', { ...registration.value, event_id: eventId });
  tenantId.value = result.tenant_id;
  uiLocale.value = result.default_locale;
  await router.push('/onboarding');
}
async function verify() { await request('/api/saas/onboarding/verify', 'POST', { token: token.value || null }); token.value = ''; await load(); }
async function select(action: string) {
  await request('/api/billing/' + action, 'POST', { plan_id: selectedPlan.value, interval: interval.value, event_id: crypto.randomUUID(), confirmed: true });
  await load(); notice.value = t('saved');
}
async function pay(id: string) { await request(`/api/billing/invoices/${id}/mock-pay`, 'POST', { confirmed: true, event_id: crypto.randomUUID() }); await load(); }
async function exportTenant() {
  const data = await request('/api/privacy/export');
  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' }));
  const link = document.createElement('a'); link.href = url; link.download = 'tenant-export.json'; link.click(); URL.revokeObjectURL(url);
}
async function rotateCredential() {
  await request('/api/credentials', 'PUT', { name: credentialName.value, value: credentialValue.value, confirmed: true });
  credentialValue.value = ''; await load(); notice.value = t('saved');
}
</script>
<template>
  <div class="page-heading">
<h1>{{ t(page) }}</h1><button :disabled="busy" @click="run(load)">
{{ t('refresh') }}
</button>
</div>
  <p class="banner">
{{ t('saasMockNotice') }}
</p>
  <p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" class="error" role="alert">
{{ error }}
</p><p v-if="notice" role="status">
{{ notice }}
</p>
  <article>
<label>{{ t('tenant') }}<input v-model="tenantSelection"></label><button :disabled="busy" @click="tenantId = tenantSelection">
{{ t('switchTenant') }}
</button>
</article>
  <template v-if="page === 'onboarding'">
    <article>
<h2>{{ t('registerOrganization') }}</h2><form @submit.prevent="run(register)">
<fieldset :disabled="busy">
      <label>{{ t('organizationName') }}<input v-model="registration.name" required maxlength="120"></label>
      <label>{{ t('administratorEmail') }}<input v-model="registration.email" type="email" required maxlength="200"></label>
      <label>{{ t('defaultLanguage') }}<select v-model="registration.default_locale" :aria-label="t('defaultLanguage')"><option v-for="locale in ['bg-BG', 'en-US']" :key="locale" :value="locale">{{ t(locale) }}</option></select></label>
      <label>{{ t('timezone') }}<input v-model="registration.timezone" required></label>
      <label>{{ t('subscriptionPlan') }}<select v-model="registration.plan_id" :aria-label="t('subscriptionPlan')"><option v-for="plan in plans" :key="plan.id" :value="plan.id">{{ uiLocale === 'bg-BG' ? plan.name_bg : plan.name_en }}</option></select></label>
      <button>{{ t('registerOrganization') }}</button>
    </fieldset>
</form>
</article>
    <article v-if="state.tenant_id">
<h2>{{ t('onboardingStatus') }}</h2><p>{{ t(state.state) }} · {{ t(state.default_locale) }} · {{ state.timezone }}</p>
      <template v-if="!state.email_verified">
<p>{{ state.verification_message }}</p>
        <button v-if="state.verification_provider === 'MOCK'" :disabled="busy" @click="run(async () => { token = (await request('/api/saas/onboarding/mock-email')).token; })">
{{ t('readMockVerification') }}
</button>
        <form @submit.prevent="run(verify)">
<label>{{ t('verificationCode') }}<input v-model="token" type="password" autocomplete="off"></label><button :disabled="busy">
{{ t('verifyEmail') }}
</button>
</form>
      </template>
      <template v-else>
<p>{{ t('emailVerified') }}</p><label>{{ t('subscriptionPlan') }}<select v-model="selectedPlan" :aria-label="t('subscriptionPlan')"><option v-for="plan in plans" :key="plan.id" :value="plan.id">{{ uiLocale === 'bg-BG' ? plan.name_bg : plan.name_en }}</option></select></label>
        <button :disabled="busy" @click="run(() => select('trial'))">
{{ t('startTrial') }}
</button><RouterLink to="/billing">
{{ t('billing') }}
</RouterLink><RouterLink to="/assistants">
{{ t('assistants') }}
</RouterLink><RouterLink to="/channels">
{{ t('channels') }}
</RouterLink><RouterLink to="/setup">
{{ t('guidedSetup') }}
</RouterLink>
      </template>
    </article>
  </template>
  <template v-if="page === 'billing'">
    <p v-if="!canConfigure">
{{ t('adminOnly') }}
</p>
    <article v-if="canConfigure">
<h2>{{ t('subscriptionStatus') }}</h2><p>{{ t(state.subscription?.status || 'notConfigured') }}</p>
      <p v-if="state.subscription?.period_end">
{{ t('periodEnd') }}: {{ date(state.subscription.period_end, timezone) }}
</p>
      <p v-if="state.subscription?.grace_until">
{{ t('gracePeriod') }}: {{ date(state.subscription.grace_until, timezone) }}
</p>
      <label>{{ t('subscriptionPlan') }}<select v-model="selectedPlan" :aria-label="t('subscriptionPlan')"><option v-for="plan in plans" :key="plan.id" :value="plan.id">{{ uiLocale === 'bg-BG' ? plan.name_bg : plan.name_en }} · {{ money(plan.monthly_minor_text, plan.currency) }}</option></select></label>
      <label>{{ t('billingInterval') }}<select v-model="interval"><option value="monthly">{{ t('monthly') }}</option><option value="annual">{{ t('annual') }}</option></select></label>
      <div class="controls">
<button :disabled="busy" @click="run(() => select('checkout'))">
{{ t('prepareCheckout') }}
</button><button :disabled="busy" @click="run(() => select('change'))">
{{ t('changePlan') }}
</button><button :disabled="busy" @click="run(async () => { await request('/api/billing/cancel', 'POST', { confirmed: true }); await load(); })">
{{ t('cancelSubscription') }}
</button>
</div>
      <p>{{ t('planChangePolicy') }}</p>
    </article>
    <article v-if="canConfigure">
<h2>{{ t('invoices') }}</h2><div class="table-wrap">
<table>
<thead><tr><th>{{ t('invoiceDate') }}</th><th>{{ t('amount') }}</th><th>{{ t('status') }}</th><th>{{ t('action') }}</th></tr></thead><tbody>
      <tr v-for="invoice in state.invoices || []" :key="invoice.id">
<td>{{ date(invoice.created_at, timezone) }}</td><td>{{ money(invoice.amount_minor_text || invoice.amount_minor, invoice.currency) }}</td><td>{{ t(invoice.status) }}</td><td>
<button v-if="invoice.status !== 'paid'" :disabled="busy" @click="run(() => pay(invoice.id))">
{{ t('simulatePayment') }}
</button>
</td>
</tr>
    </tbody>
</table>
</div><EmptyState v-if="!state.invoices?.length" :title="t('empty')" />
</article>
    <article v-if="canConfigure">
<h2>{{ t('billingNotifications') }}</h2><p v-for="event in (state.notifications || []).filter((n: any) => n.kind === 'billing_notification')" :key="event.id">
{{ event.subject }} · {{ event.body }}
</p>
</article>
  </template>
  <template v-if="page === 'usage' || page === 'billing' && canConfigure">
    <article>
<h2>{{ t('usage') }}</h2><p>{{ t('billingPeriod') }}: {{ (page === 'usage' ? state : state.usage)?.billing_period }}</p><p>{{ t('tokenUsageNotice') }}</p>
      <p v-for="warning in (page === 'usage' ? state : state.usage)?.warnings || []" :key="warning.id" class="banner">
{{ t(warning.code) }} · {{ t(warning.category) }}
</p>
      <div class="table-wrap">
<table>
<thead><tr><th>{{ t('usageCategory') }}</th><th>{{ t('quantity') }}</th><th>{{ t('reservedQuantity') }}</th><th>{{ t('planLimit') }}</th><th>{{ t('policy') }}</th></tr></thead><tbody>
        <tr v-for="(value, category) in (page === 'usage' ? state : state.usage)?.usage || {}" :key="category">
<td>{{ t(String(category)) }}</td><td>{{ number((value as any).quantity) }}</td><td>{{ number((value as any).reserved_quantity || 0) }}</td><td>{{ (value as any).limit ? number((value as any).limit.maximum) : t('notConfigured') }}</td><td>{{ t((value as any).limit?.mode || 'notConfigured') }}</td>
</tr>
      </tbody>
</table>
</div>
    </article>
  </template>
  <template v-if="page === 'operations'">
    <p class="banner">
{{ t('operationMetricsScope') }}
</p>
    <article>
<h2>{{ t('workerHealth') }}</h2><p>{{ t(state.worker?.status || 'notConfigured') }}</p><p v-if="state.worker?.last_tick_at">
{{ date(state.worker.last_tick_at, timezone) }}
</p>
      <div class="table-wrap">
<table>
<thead><tr><th>{{ t('operation') }}</th><th>{{ t('sampleCount') }}</th><th>{{ t('errors') }}</th><th>{{ t('meanLatencyMs') }}</th></tr></thead><tbody>
<tr v-for="(metric, name) in state.metrics || {}" :key="name">
<td>{{ t(String(name)) }}</td><td>{{ number((metric as any).count) }}</td><td>{{ number((metric as any).errors) }}</td><td>{{ number((metric as any).mean_ms) }}</td>
</tr>
</tbody>
</table>
</div>
    </article>
    <article>
<h2>{{ t('failedJobs') }}</h2><p v-for="job in state.failed_jobs || []" :key="job.id">
{{ t(job.kind) }} · {{ t(job.status) }} · {{ t(job.error_code) }} · {{ number(job.attempts || 0) }}
</p>
</article>
    <article v-if="canConfigure">
<h2>{{ t('credentialManagement') }}</h2><form @submit.prevent="run(rotateCredential)">
<label>{{ t('credentialName') }}<input v-model="credentialName" required></label><label>{{ t('credentialValue') }}<input v-model="credentialValue" type="password" minlength="16" required autocomplete="new-password"></label><button :disabled="busy">
{{ t('rotateCredential') }}
</button>
</form>
      <p v-for="credential in credentials" :key="credential.id">
{{ credential.name }} · {{ t(credential.state || 'active') }} · {{ number(credential.version || 1) }} <button :disabled="busy" @click="run(async () => { await request(`/api/credentials/${credential.id}/revoke`, 'POST', { confirmed: true }); await load(); })">
{{ t('revoke') }}
</button>
</p>
      <button :disabled="busy" @click="run(exportTenant)">
{{ t('exportTenant') }}
</button>
    </article>
  </template>
  <template v-if="page === 'administration'">
<article>
<h2>{{ t('tenantOverview') }}</h2><p>{{ t('supportScopeNotice') }}</p><p v-for="tenant in tenants" :key="tenant.id">
{{ tenant.name }} · {{ t(tenant.state) }} · {{ t(tenant.subscription_status) }} · {{ number(tenant.counts.users) }}
</p>
</article>
</template>
</template>
