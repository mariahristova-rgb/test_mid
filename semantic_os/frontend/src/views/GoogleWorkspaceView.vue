<script setup lang="ts">
import {onMounted,ref,computed} from 'vue';
import {request} from '../services/api';
import {t} from '../services/i18n';
const access=ref<any>({}),connections=ref<any[]>([]),policy=ref<any>(null),busy=ref(false),error=ref(''),notice=ref('');
const allowed=computed(()=>access.value.user?.role==='admin');
const form=ref({kind:'calendar',client_id:'',client_secret:'',redirect_uri:window.location.origin+'/backend/api/google/oauth/callback',expected_account:'mariya.manolova92@gmail.com'});
async function run(action:()=>Promise<unknown>){if(busy.value)return;busy.value=true;error.value='';notice.value='';try{await action();}catch(e){error.value=e instanceof Error?e.message:t('error');}finally{busy.value=false;}}
async function load(){access.value=await request('/api/bootstrap');if(allowed.value)[connections.value,policy.value]=await Promise.all([request('/api/google'),request('/api/concierge/policy')]);}
async function saveClient(){try{await request('/api/google/config','POST',form.value);await load();notice.value=t('saved');}finally{form.value.client_secret='';}}
async function connect(kind:string){const result=await request('/api/google/oauth/'+kind,'POST',{});window.location.assign(result.authorize_url);}
async function revoke(kind:string){await request('/api/google/revoke/'+kind,'POST',{});await load();}
async function savePolicy(){await request('/api/concierge/policy','PUT',policy.value);await load();notice.value=t('saved');}
onMounted(()=>void run(load));
</script>
<template>
<h1>{{ t('googleWorkspace') }}</h1><p>{{ t('googleSetupNotice') }}</p><p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" role="alert">
{{ error }}
</p><p v-if="notice" role="status">
{{ notice }}
</p><p v-if="access.user && !allowed">
{{ t('forbidden') }}
</p><template v-if="allowed">
<article>
<h2>{{ t('googleClient') }}</h2><form @submit.prevent="run(saveClient)">
<fieldset :disabled="busy">
<label>{{ t('googleConnectionKind') }}<select v-model="form.kind"><option value="calendar">{{ t('googleCalendar') }}</option><option value="gmail">{{ t('gmailSending') }}</option></select></label><label>{{ t('googleClientId') }}<input v-model="form.client_id" required autocomplete="off"></label><label>{{ t('googleClientSecret') }}<input v-model="form.client_secret" type="password" required autocomplete="new-password"></label><label>{{ t('googleRedirect') }}<input v-model="form.redirect_uri" type="url" required></label><p>{{ form.expected_account }}</p><button>{{ t('save') }}</button>
</fieldset>
</form>
</article>
<article>
<h2>{{ t('googleConnections') }}</h2><button :disabled="busy" @click="run(load)">
{{ t('refresh') }}
</button><section v-for="connection in connections" :key="connection.connection">
<h3>{{ t(connection.connection==='calendar'?'googleCalendar':'gmailSending') }}</h3><p>{{ t(connection.state) }} {{ connection.account }}</p><button :disabled="busy" @click="run(()=>connect(connection.connection))">
{{ t('googleConnect') }}
</button><button :disabled="busy" @click="run(()=>revoke(connection.connection))">
{{ t('googleDisconnect') }}
</button>
</section>
</article>
<article v-if="policy">
<h2>{{ t('conciergePolicy') }}</h2><form @submit.prevent="run(savePolicy)">
<fieldset :disabled="busy">
<label><input v-model="policy.enabled" type="checkbox">{{ t('conciergeEnable') }}</label><label>{{ t('googleCalendarId') }}<input v-model="policy.calendar_id" required></label><p>{{ t('conciergeHours') }}</p><label>{{ t('duration') }}<input v-model.number="policy.duration_minutes" type="number" min="15" max="120" required></label><label>{{ t('conciergeBuffer') }}<input v-model.number="policy.buffer_minutes" type="number" min="0" max="60" required></label><label>{{ t('conciergeCutoff') }}<input v-model="policy.ends_on" type="date" required></label><label>{{ t('conciergeReminder') }}<input v-model="policy.reminder_time" type="time" required></label><label>{{ t('conciergeFallback') }}<input v-model.number="policy.fallback_minutes" type="number" min="5" max="120" required></label><label>{{ t('conciergeRetention') }}<input v-model.number="policy.request_retention_days" type="number" min="1" :max="access.tenant.retention_days" required></label><label>{{ t('conciergeInbox') }}<input v-model="policy.business_inbox" type="email" required></label><label>{{ t('conciergeManagementOrigin') }}<input v-model="policy.management_origin" type="url" required></label><label><input v-model="policy.meet_authorized" type="checkbox">{{ t('conciergeMeetAuthorization') }}</label><label><input v-model="policy.operations_authorized" type="checkbox">{{ t('conciergeLiveAuthorization') }}</label><button>{{ t('save') }}</button>
</fieldset>
</form>
</article>
</template>
</template>
