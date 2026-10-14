<script setup lang="ts">
import {onMounted,ref} from 'vue';
import {request} from '../services/api';
import {customerAuthorizationURL} from '../services/customer-authorization.mjs';
import {t} from '../services/i18n';
import {useRoute} from 'vue-router';
const route=useRoute();
const catalog=ref<any[]>([]),connections=ref<any[]>([]),resources=ref<Record<string,any[]>>({});
const actions=ref<Record<string,string[]>>({}),bookingConsent=ref<Record<string,boolean>>({});
const selected=ref<Record<string,string>>({}),error=ref(''),busy=ref(false),confirm=ref<Record<string,boolean>>({});
async function load(){[catalog.value,connections.value]=await Promise.all([request('/api/customer-connectors'),request('/api/customer-connectors/connections')]);for(const provider of catalog.value)actions.value[provider.provider]??=[provider.actions[0]];}
async function run(action:()=>Promise<unknown>){if(busy.value)return;busy.value=true;error.value='';try{await action();}catch{error.value=t('customerConnectionError');}finally{busy.value=false;}}
async function connect(provider:string){
  const row=await request('/api/customer-connectors/connections','POST',{provider,actions:actions.value[provider],revision:1});
  await authorize(row);
}
async function authorize(row:any){
  const result=await request(`/api/customer-connectors/connections/${row.id}/authorize`,'POST',{revision:row.revision});
  window.location.assign(customerAuthorizationURL(result.authorization_url,row.provider));
}
async function enableBooking(row:any){if(!bookingConsent.value[row.id])return;await request(`/api/customer-connectors/connections/${row.id}/booking/enable`,'POST',{revision:row.revision,confirmed:true});await load();}
async function discover(row:any){resources.value[row.id]=await request(`/api/customer-connectors/connections/${row.id}/resources`);}
async function select(row:any){if(!selected.value[row.id])return;await request(`/api/customer-connectors/connections/${row.id}/resources`,'PUT',{revision:row.revision,resource_ids:[selected.value[row.id]]});await load();}
async function disconnect(row:any){if(!confirm.value[row.id])return;await request(`/api/customer-connectors/connections/${row.id}/disconnect`,'POST',{revision:row.revision});confirm.value[row.id]=false;delete resources.value[row.id];delete selected.value[row.id];await load();}
onMounted(()=>run(async()=>{await load();if(route.query.connection==='denied')error.value=t('customerConnectionError');}));
</script>
<template>
<section :aria-label="t('customerConnections')" :aria-busy="busy">
<h2>{{ t('customerConnections') }}</h2><p>{{ t('customerConnectionHelp') }}</p>
<p v-if="error" role="alert">
{{ error }}
</p>
<fieldset :disabled="busy">
<section v-for="provider in catalog" :key="provider.provider" class="integration-row">
<div>
<h3>{{ t('businessProvider_'+provider.provider) }}</h3><div class="checks">
<label v-for="action in provider.actions" :key="action"><input v-model="actions[provider.provider]" type="checkbox" :value="action" :disabled="!provider.configured">{{ t('customerAction_'+action) }}</label>
</div><p v-if="!provider.configured">
{{ t('customerAppMissing') }}
</p>
</div>
<button class="button-primary" :disabled="!provider.configured || !actions[provider.provider]?.length" @click="run(()=>connect(provider.provider))">
{{ t('customerAuthorize') }}
</button>
</section>
<article v-for="row in connections" :key="row.id">
<h3>{{ t('businessProvider_'+row.provider) }}</h3><p>{{ t('customerState_'+row.state) }} · {{ t(row.verification) }}</p>
<p v-if="row.booking_enabled" role="status">
{{ t('customerBookingEnabled') }}
</p>
<p>{{ t('customerConsentActions') }}: {{ row.actions.map((value:string)=>t('customerAction_'+value)).join(', ') }}</p>
<div class="page-actions">
<button v-if="['disconnected','authorization_pending','reauthorization_required','degraded'].includes(row.state)" @click="run(()=>authorize(row))">
{{ t('customerAuthorize') }}
</button>
<button v-if="['connected_unverified','verified'].includes(row.state)" @click="run(()=>discover(row))">
{{ t('customerDiscover') }}
</button>
</div>
<form v-if="resources[row.id]" @submit.prevent="run(()=>select(row))">
<label>{{ t('customerResource') }}<select v-model="selected[row.id]" required><option value="">{{ t('select') }}</option><option v-for="resource in resources[row.id]" :key="resource.id" :value="resource.id">{{ resource.primary ? t('customerPrimaryCalendar') : resource.ordinal ? t('customerResource')+' '+resource.ordinal : resource.id }}</option></select></label>
<button :disabled="!selected[row.id]">
{{ t('save') }}
</button>
</form>
<template v-if="row.provider==='google' && row.resource_ids?.length && row.actions.includes('create') && !row.booking_enabled">
<label class="check"><input v-model="bookingConsent[row.id]" type="checkbox">{{ t('customerBookingConsent') }}</label><button :disabled="!bookingConsent[row.id]" @click="run(()=>enableBooking(row))">
{{ t('customerEnableBooking') }}
</button>
</template>
<label class="check"><input v-model="confirm[row.id]" type="checkbox">{{ t('customerDisconnectConsent') }}</label>
<button class="button-destructive" :disabled="!confirm[row.id]" @click="run(()=>disconnect(row))">
{{ t('customerDisconnect') }}
</button>
</article>
</fieldset>
</section>
</template>
