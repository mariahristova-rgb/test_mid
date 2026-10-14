<script setup lang="ts">
import {ref} from 'vue';
import {request} from '../services/api';
import {t} from '../services/i18n';
const catalog=ref<any[]>([]),connections=ref<any[]>([]),quotes=ref<any[]>([]),busy=ref(false),error=ref(''),receipt=ref<any>(null);
const provider=ref('google'),selectedActions=ref<string[]>(['availability']),consent=ref(false);
const quoteForm=ref({tier:'simple',system:'rest',objects:['contacts'],direction:'one_way',authentication:'oauth',environments:1,custom_sla:false});
async function run(action:()=>Promise<void>){if(busy.value)return;busy.value=true;error.value='';try{await action();}catch(e){error.value=e instanceof Error?e.message:t('error');}finally{busy.value=false;}}
async function load(){catalog.value=await request('/api/connectors');[connections.value,quotes.value]=await Promise.all([request('/api/connectors/connections'),request('/api/connectors/quotes')]);}
function choose(){selectedActions.value=[catalog.value.find(item=>item.provider===provider.value)?.fixture_actions[0]].filter(Boolean);}
async function create(){await request('/api/connectors/connections','POST',{provider:provider.value,actions:selectedActions.value,resource_ids:['fixture-primary']});await load();}
async function connect(row:any){
  const start=await request('/api/connectors/connections/'+row.id+'/oauth/start','POST',{revision:row.revision});
  // Fixture protocol only: never navigate the vendor URL, persist state, or accept a real code.
  await request('/api/connectors/connections/'+row.id+'/oauth/complete','POST',{state:start.state,binding:start.binding,code:'fixture-code'});await load();
}
async function disconnect(row:any){await request('/api/connectors/connections/'+row.id+'/disconnect','POST',{revision:row.revision});await load();}
async function resources(row:any){receipt.value=await request('/api/connectors/connections/'+row.id+'/resources');}
async function preview(row:any,action:string){receipt.value=await request('/api/connectors/connections/'+row.id+'/preview','POST',{
  revision:row.revision,action,resource_id:'fixture-primary',key:crypto.randomUUID(),consent:consent.value,locale:document.documentElement.lang,
  arguments:{start:'2030-10-09T12:00:00Z',end:'2030-10-09T12:30:00Z',event_id:'fixture-owned',etag:'fixture-etag',properties:{email:'synthetic@example.invalid',firstname:'Synthetic',company:'Fixture'}}});await load();}
async function quote(){receipt.value=await request('/api/connectors/quotes','POST',{...quoteForm.value,key:crypto.randomUUID()});await load();}
</script>
<template>
<section aria-labelledby="connector-workspace-heading">
<h3 id="connector-workspace-heading">
{{ t('connectorWorkspace') }}
</h3>
<p>{{ t('connectorWorkspaceHelp') }}</p>
<button :disabled="busy" @click="run(load)">
{{ t('connectorLoad') }}
</button>
<p v-if="busy" role="status">
{{ t('busy') }}
</p>
<p v-if="error" role="alert">
{{ error }}
</p>
<template v-if="catalog.length">
<form @submit.prevent="run(create)">
<fieldset :disabled="busy">
<legend>{{ t('connectorCreateFixture') }}</legend>
<label>{{ t('connectorProvider') }}<select v-model="provider" @change="choose"><option v-for="item in catalog" :key="item.provider" :value="item.provider">{{ t('connector_'+item.provider) }}</option></select></label>
<label v-for="action in catalog.find(item=>item.provider===provider)?.fixture_actions" :key="action"><input v-model="selectedActions" type="checkbox" :value="action">{{ t('connectorAction_'+action) }}</label>
<button :disabled="!selectedActions.length">
{{ t('connectorCreateFixture') }}
</button>
</fieldset>
</form>
<label><input v-model="consent" type="checkbox">{{ t('connectorFixtureConsent') }}</label>
<p>{{ t('connectorPreviewDate') }}</p>
<article v-for="row in connections" :key="row.id">
<h4>{{ t('connector_'+row.provider) }}</h4>
<p>{{ t('connectorSimulation') }} · {{ t('connectorState_'+(row.state==='needs_reauthorization'?'reauthorization':row.state)) }} · {{ t('connectorRevision') }} {{ row.revision }}</p>
<p v-if="row.failure_code" role="status">
{{ t(row.failure_code) }}
</p>
<button :disabled="busy || row.failure_code==='delivery_unknown'" @click="run(()=>connect(row))">
{{ t('connectorOAuthFixture') }}
</button>
<button :disabled="busy || row.state!=='connected'" @click="run(()=>resources(row))">
{{ t('connectorDiscoverFixture') }}
</button>
<button v-for="action in row.actions" :key="action" :disabled="busy || row.state!=='connected' || (['create','reschedule','cancel','contact_write'].includes(action) && !consent)" @click="run(()=>preview(row,action))">
{{ t('connectorAction_'+action) }}
</button>
<button :disabled="busy" @click="run(()=>disconnect(row))">
{{ t('connectorDisconnectFixture') }}
</button>
</article>
<form @submit.prevent="run(quote)">
<fieldset :disabled="busy">
<legend>{{ t('connectorQuoteScoping') }}</legend>
<label>{{ t('connectorQuoteTier') }}<select v-model="quoteForm.tier"><option value="simple">Simple</option><option value="advanced">Advanced</option><option value="enterprise">Enterprise</option></select></label>
<label>{{ t('connectorQuoteSystem') }}<select v-model="quoteForm.system"><option value="rest">REST</option><option value="crm">CRM</option><option value="erp">ERP</option><option value="legacy">{{ t('connectorLegacy') }}</option></select></label>
<label>{{ t('connectorQuoteDirection') }}<select v-model="quoteForm.direction"><option value="one_way">{{ t('connectorOneWay') }}</option><option value="bidirectional">{{ t('connectorTwoWay') }}</option></select></label>
<label>{{ t('connectorQuoteAuth') }}<select v-model="quoteForm.authentication"><option value="oauth">OAuth</option><option value="api_key">{{ t('connectorApiKeyMethod') }}</option><option value="service_account">{{ t('connectorServiceAccount') }}</option><option value="unknown">{{ t('connectorUnknown') }}</option></select></label>
<label>{{ t('connectorQuoteObjects') }}<select v-model="quoteForm.objects" multiple required><option v-for="object in ['contacts','appointments','leads','inventory','orders']" :key="object" :value="object">{{ t('connectorObject_'+object) }}</option></select></label>
<label>{{ t('connectorQuoteEnvironments') }}<input v-model.number="quoteForm.environments" type="number" min="1" max="10" required></label>
<label><input v-model="quoteForm.custom_sla" type="checkbox">{{ t('connectorQuoteSla') }}</label>
<button>{{ t('connectorQuoteRequest') }}</button>
</fieldset>
</form>
<p v-for="item in quotes" :key="item.id">
{{ item.requirements.tier }} · {{ t('connectorScopingRequired') }}
</p>
<section v-if="receipt" aria-live="polite">
<h4>{{ t('connectorFixtureReceipt') }}</h4>
<p>{{ t('connectorSimulation') }}</p>
<p v-if="receipt.available!==undefined">
{{ t(receipt.available?'connectorAvailable':'connectorUnavailable') }}
</p>
<p v-if="receipt.status==='SCOPING_REQUIRED'">
{{ t('connectorScopingRequired') }}
</p>
<p v-if="receipt.status==='SIMULATED'">
{{ t('PASS') }} · {{ t('MOCK_ONLY') }}
</p>
<ul v-if="receipt.resources">
<li v-for="resource in receipt.resources" :key="resource.id">
{{ resource.id }}
</li>
</ul>
</section>
</template>
</section>
</template>
