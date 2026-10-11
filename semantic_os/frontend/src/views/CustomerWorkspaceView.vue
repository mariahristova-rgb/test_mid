<script setup lang="ts">
import { computed, onMounted, ref, watch, onUnmounted } from 'vue';
import { useRoute } from 'vue-router';
import { request, tenantId } from '../services/api';
import { t, number } from '../services/i18n';
const route=useRoute();
const page=computed(()=>String(route.meta.page));
const state=ref<any>({}),error=ref(''),busy=ref(false),days=ref(30),offset=ref(0);
const access=ref<any>({}),details=ref<Record<string,any>>({});
const canOperate=computed(()=>['admin','operator'].includes(access.value.user?.role));
let epoch=0;
const paths:Record<string,string>={progress:'progress',health:'health',quality:'quality',analytics:'analytics',leads:'requests'};
async function load(){
  const generation=++epoch;busy.value=true;error.value='';state.value={};details.value={};access.value={};
  try{
    const query=page.value==='analytics'?`?days=${days.value}`:page.value==='leads'?`?limit=25&offset=${offset.value}`:'';
    const [result,bootstrap]=await Promise.all([request('/api/workspace/'+paths[page.value]+query),request('/api/bootstrap')]);
    if(generation===epoch){state.value=result;access.value=bootstrap;}
  }catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}
  finally{if(generation===epoch)busy.value=false;}
}
async function revealRequest(id:string){const generation=epoch;busy.value=true;error.value='';try{const row=await request(`/api/workspace/requests/${id}`);if(generation===epoch)details.value={...details.value,[id]:row};}catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}finally{if(generation===epoch)busy.value=false;}}
async function updateRequest(item:any,state:string){const generation=epoch;busy.value=true;error.value='';try{await request(`/api/workspace/requests/${item.id}`,'PUT',{revision:item.request_revision||0,state,assigned_user_id:access.value.user.id});if(generation===epoch)await load();}catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}finally{if(generation===epoch)busy.value=false;}}
async function review(id:string,decision:string){
  busy.value=true;error.value='';
  try{await request(`/api/workspace/quality/${id}/review`,'POST',{decision});await load();}
  catch(e){error.value=e instanceof Error?e.message:t('error');}
  finally{busy.value=false;}
}
watch([page,tenantId],()=>{offset.value=0;void load();});
onMounted(()=>void load());onUnmounted(()=>epoch++);
</script>
<template>
  <div class="page-heading">
<h1>{{ t(page) }}</h1><button :disabled="busy" @click="load">
{{ t('refresh') }}
</button>
</div>
  <p class="banner">
{{ t('p16ScopeNotice') }}
</p>
  <p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" class="error" role="alert">
{{ error }}
</p>
  <p v-if="state.truncated" role="status">
{{ t('p16BoundedNotice') }}
</p>
  <template v-if="page==='progress' && state.steps">
    <article><h2>{{ t('p16TimeToValue') }}</h2><p>{{ t('p16FirstPassSeconds') }}: {{ state.adoption_metrics?.time_to_first_pass_seconds==null?t('notRecorded'):number(state.adoption_metrics.time_to_first_pass_seconds) }}</p><p>{{ t('p16FirstWidgetSeconds') }}: {{ state.adoption_metrics?.time_to_first_published_widget_seconds==null?t('notRecorded'):number(state.adoption_metrics.time_to_first_published_widget_seconds) }}</p><p>{{ t('p16AdoptionNotice') }}</p></article>
    <article>
<h2>{{ t('p16NextSteps') }}</h2><ol>
<li v-for="step in state.steps" :key="step.key">
<RouterLink :to="step.path">
{{ t('p16Step_'+step.key) }}
</RouterLink> · {{ t(step.complete?'PASS':'BLOCKED') }}
</li>
</ol><p>{{ t('p16InstallationUnverified') }}</p>
</article>
    <article v-for="draft in state.drafts" :key="draft.id">
<h2>{{ draft.name }}</h2><RouterLink :to="{path:'/setup',query:{draft:draft.id}}">
{{ t('resumeSetup') }}
</RouterLink><p v-for="reason in draft.reasons" :key="reason">
{{ t(reason) }}
</p><p v-if="!draft.reasons.length">
{{ t('p16MockReady') }}
</p>
</article>
    <p v-if="!state.drafts.length">
{{ t('p16NoDraft') }} <RouterLink to="/setup">
{{ t('guidedSetup') }}
</RouterLink>
</p>
  </template>
  <template v-if="page==='health' && state.assistants">
    <article v-for="assistant in state.assistants" :key="assistant.id">
      <h2>{{ assistant.name }}</h2><p>{{ t('p16Knowledge') }}: {{ number(assistant.knowledge_entries) }} · {{ t('p16Tools') }}: {{ number(assistant.tool_count) }}</p>
      <p>{{ assistant.locales.map((locale:string)=>t(locale)).join(' · ') }}</p><p>{{ t(assistant.llm_status) }} · {{ t(assistant.agents_enabled?'p16AgentsEnabled':'p16AgentsBlocked') }}</p>
      <p>{{ t('p16VoiceUnverified') }}</p><p v-if="!assistant.readiness">
{{ t('p16NoCurrentProof') }}
</p>
      <ul v-else>
<li v-for="reason in assistant.readiness.reasons" :key="reason">
{{ t(reason) }}
</li>
</ul>
      <RouterLink v-if="assistant.draft_id && canOperate" :to="{path:'/testing',query:{draft:assistant.draft_id}}">
{{ t('testing') }}
</RouterLink>
    </article>
    <article>
<h2>{{ t('p16Connections') }}</h2><p v-for="connection in state.connections" :key="connection.kind">
{{ t(connection.kind) }} · {{ t(connection.state) }} · {{ t('p16NotCertified') }}
</p><p>{{ t('failedJobs') }}: {{ number(state.unresolved_jobs) }}</p>
</article>
  </template>
  <template v-if="page==='quality' && state.suggestions">
    <p v-for="(count,category) in state.groups||{}" :key="category">
{{ t('p16Signal_'+String(category)) }}: {{ number(Number(count)) }}
</p>
    <p>{{ t('p16QualityNotice') }}</p><p v-if="!state.suggestions.length">
{{ t('p16NoSignals') }}
</p>
    <article v-for="signal in state.suggestions" :key="signal.id">
<h2>{{ t('p16Signal_'+signal.category) }}</h2><p>{{ t('p16Provenance') }}: {{ signal.source_id }}</p><p>{{ t('scenario_'+signal.scenario) }} · {{ t('bg-BG') }} / {{ t('en-US') }} · {{ t('p16Decision_'+signal.decision) }}</p><div class="controls">
<p>{{ t('p16Source_'+signal.provenance) }}</p>
<button :disabled="busy" @click="review(signal.id,'accepted')">
{{ t('p16AcceptSuggestion') }}
</button><button :disabled="busy" @click="review(signal.id,'dismissed')">
{{ t('p16DismissSuggestion') }}
</button><RouterLink :to="{path:'/testing',query:{scenario:signal.scenario}}">
{{ t('testing') }}
</RouterLink>
</div>
</article>
  </template>
  <template v-if="page==='analytics' && state.conversations">
    <article>
<h2>{{ t('p16ConsentedFunnel') }}</h2><p>{{ t('p16FunnelNotice') }}</p><p v-if="!state.funnel?.length">
{{ t('p16NoConsentedEvents') }}
</p><p v-for="(row,index) in state.funnel||[]" :key="index">
{{ t('p16Stage_'+row.stage) }} · {{ t(row.locale) }} · {{ t('p16Scope_'+row.scope) }}: {{ number(row.quantity) }}
</p>
</article>
    <form class="controls" @submit.prevent="load">
<label>{{ t('p16Days') }}<input v-model.number="days" type="number" min="1" max="90" required></label><button :disabled="busy">
{{ t('refresh') }}
</button>
</form>
    <p>{{ t('p16AnalyticsNotice') }}</p><article>
<h2>{{ t('inbox') }}</h2><p v-for="(row,index) in state.conversations" :key="index">
{{ t(row.channel) }} · {{ t(row.locale) }}: {{ number(row.quantity) }}
</p><p v-if="!state.conversations.length">
{{ t('empty') }}
</p>
</article>
    <article>
<h2>{{ t('appointments') }}</h2><p v-for="(row,index) in state.appointments" :key="index">
{{ t(row.status) }}: {{ number(row.quantity) }}
</p><p>{{ t('p16UnmeasuredFunnel') }}</p>
</article>
  </template>
  <template v-if="page==='leads' && state.items">
    <p>{{ t('p16LeadPrivacy') }}</p><article v-for="item in state.items" :key="item.id">
<h2>{{ t('p16Request_'+item.action) }}</h2><p>{{ t(item.operator_state||item.status) }} · {{ t(item.locale) }}</p><RouterLink :to="{path:'/inbox',query:{conversation:item.conversation_id}}">
{{ t('inbox') }}
</RouterLink>
<div v-if="canOperate" class="controls">
<button :disabled="busy" @click="revealRequest(item.id)">
{{ t('p16RevealRequest') }}
</button><button :disabled="busy" @click="updateRequest(item,'in_progress')">
{{ t('assignToMe') }}
</button><button :disabled="busy" @click="updateRequest(item,'resolved')">
{{ t('queue_resolved') }}
</button>
</div>
<dl v-if="details[item.id]">
<template v-for="field in ['name','email','company','topic','timeline','impact']" :key="field">
<dt>{{ t('p16Field_'+field) }}</dt><dd>{{ details[item.id][field]||t('notRecorded') }}</dd>
</template>
</dl>
</article><p v-if="!state.items.length">
{{ t('empty') }}
</p><div class="controls">
<button :disabled="busy || !offset" @click="offset=Math.max(0,offset-25);load()">
{{ t('previous') }}
</button><button :disabled="busy || !state.has_more" @click="offset+=25;load()">
{{ t('next') }}
</button>
</div>
  </template>
</template>
