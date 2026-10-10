<script setup lang="ts">
import { computed, ref } from 'vue';
import { request } from '../services/api';
import { t, number } from '../services/i18n';
const props = defineProps<{ assistants: any[]; connections: any[]; allowed: boolean }>();
const emit = defineEmits<{ refresh: [] }>();
const busy = ref(false), error = ref('');
const config = ref<any>({ assistant_id: 'default', channel: 'email', provider: 'mock', sender_id: '', public_origin: '',
  webhook_secret: '', app_secret: '', verify_token: '', access_token: '', auth_token: '', smtp_password: '',
  waba_id: '', phone_number_id: '', api_version: '', account_sid: '', smtp_host: '', smtp_username: '', smtp_port: 465,
  email_draft_required: true, enable_live: false, rate_per_minute: 30 });
const providerOptions = computed(() => ({ email: ['mock', 'smtp'], whatsapp: ['mock', 'meta'], sms: ['mock', 'twilio'], web_chat: ['mock'] })[config.value.channel as 'email'] || ['mock']);
const secretFields = computed(() => ({ mock: ['webhook_secret'], smtp: ['webhook_secret', 'smtp_password'], meta: ['app_secret', 'verify_token', 'access_token'], twilio: ['auth_token'] })[config.value.provider as 'mock'] || []);
const providerFields = computed(() => ({ mock: [], smtp: ['smtp_host', 'smtp_username'], meta: ['waba_id', 'phone_number_id', 'api_version'], twilio: ['account_sid'] })[config.value.provider as 'mock'] || []);
async function save() {
  busy.value = true; error.value = '';
  try {
    await request('/api/messaging/connections', 'POST', config.value);
    for (const key of ['webhook_secret', 'app_secret', 'verify_token', 'access_token', 'auth_token', 'smtp_password']) config.value[key] = '';
    emit('refresh');
  } catch (e) { error.value = e instanceof Error ? e.message : t('error'); }
  finally { busy.value = false; }
}
async function toggle(connection: any) {
  busy.value = true; error.value = '';
  try { await request(`/api/messaging/connections/${connection.id}/state`, 'PUT', { enabled: !connection.enabled, confirmed: true }); emit('refresh'); }
  catch (e) { error.value = e instanceof Error ? e.message : t('error'); }
  finally { busy.value = false; }
}
</script>
<template>
  <article v-if="allowed">
    <h2>{{ t('connectChannel') }}</h2><p>{{ t('providerSetupNotice') }}</p>
    <p v-if="error" role="alert" class="error">
{{ error }}
</p>
    <form @submit.prevent="save">
      <fieldset :disabled="busy">
        <label>{{ t('assistant') }}<select v-model="config.assistant_id"><option v-for="a in props.assistants" :key="a.id" :value="a.id">{{ a.name }}</option></select></label>
        <label>{{ t('channel') }}<select v-model="config.channel" @change="config.provider = 'mock'"><option v-for="channel in ['email', 'whatsapp', 'sms', 'web_chat']" :key="channel" :value="channel">{{ t(channel) }}</option></select></label>
        <label>{{ t('provider') }}<select v-model="config.provider"><option v-for="provider in providerOptions" :key="provider" :value="provider">{{ t(provider) }}</option></select></label>
        <label>{{ t('sender_id') }}<input v-model="config.sender_id" required maxlength="200"></label>
        <template v-if="config.provider !== 'mock'">
          <label>{{ t('public_origin') }}<input v-model="config.public_origin" type="url" required></label>
          <label v-for="field in providerFields" :key="field">{{ t(field) }}<input v-model="config[field]" required autocomplete="off"></label>
          <label v-if="config.provider === 'smtp'">{{ t('smtp_port') }}<select v-model.number="config.smtp_port"><option :value="465">{{ number(465) }}</option><option :value="587">{{ number(587) }}</option></select></label>
          <label class="check"><input v-model="config.enable_live" type="checkbox">{{ t('enableLiveMessaging') }}</label>
        </template>
        <label v-for="field in secretFields" :key="field">{{ t(field) }}<input v-model="config[field]" type="password" required :minlength="field === 'webhook_secret' ? 32 : 1" autocomplete="new-password"></label>
        <label v-if="config.channel === 'email'" class="check"><input v-model="config.email_draft_required" type="checkbox">{{ t('emailDraftRequired') }}</label>
        <label>{{ t('rate_per_minute') }}<input v-model.number="config.rate_per_minute" type="number" min="1" max="300" required></label>
        <button>{{ t('save') }}</button>
      </fieldset>
    </form>
  </article>
  <article v-for="connection in props.connections" :key="connection.id">
    <h3>{{ t(connection.channel) }} · {{ t(connection.provider) }}</h3>
    <span class="badge">{{ t(connection.enabled === false ? 'disabled' : connection.last_error ? 'error' : connection.state) }}</span>
    <p>{{ t('id') }}: {{ connection.id }}</p>
    <p v-if="connection.sender_id">
{{ t('sender_id') }}: {{ connection.sender_id }}
</p>
    <p v-if="connection.webhook_status">
{{ t('webhookStatus') }}: {{ t(connection.webhook_status) }}
</p>
    <p v-if="connection.last_error">
{{ t('lastError') }}: {{ t(connection.last_error) }}
</p>
    <p>{{ t('bg-BG') }} / {{ t('en-US') }}</p>
    <p v-if="connection.capabilities">
{{ t('capabilities') }}: {{ connection.capabilities.map((c: string) => t(c)).join(', ') }}
</p>
    <button v-if="allowed && connection.credential_names" :disabled="busy" @click="toggle(connection)">
{{ t(connection.enabled ? 'disableConnection' : 'enableConnection') }}
</button>
  </article>
</template>
