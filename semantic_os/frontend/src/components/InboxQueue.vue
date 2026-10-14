<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { request } from '../services/api';
import { t, date } from '../services/i18n';
const props=defineProps<{conversation:any;userId:string;timezone?:string}>();
const emit=defineEmits<{changed:[]}>();
const note=ref(''),notes=ref<any[]>([]),error=ref(''),notice=ref(''),busy=ref(false),revealed=ref(false);
const priority=ref('normal'),sla=ref(60),resolution=ref('answered');
const qualityCategory=ref('knowledge_gap'),qualityConfirmed=ref(false),qualityEvent=ref(crypto.randomUUID());
watch(()=>props.conversation,()=>{priority.value=props.conversation.queue_priority||'normal';sla.value=props.conversation.queue_sla_minutes||60;},{immediate:true});
let epoch=0;
watch(()=>props.conversation.id,()=>{epoch++;note.value='';notes.value=[];revealed.value=false;error.value='';notice.value='';busy.value=false;qualityConfirmed.value=false;qualityEvent.value=crypto.randomUUID();});
onUnmounted(()=>epoch++);
async function run(action:()=>Promise<void>){
  if(busy.value)return;const generation=epoch;busy.value=true;error.value='';notice.value='';
  try{await action();}catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}
  finally{if(generation===epoch)busy.value=false;}
}
async function change(state:string,settings=false,markRead=false){
  const generation=epoch;
  await request(`/api/inbox/${props.conversation.id}/queue`,'PUT',{revision:props.conversation.queue_revision||0,state,assigned_user_id:state==='assigned'?props.userId:props.conversation.queue_assigned_user_id||null,
    ...(settings?{priority:priority.value,sla_minutes:sla.value}:{}),...(state==='resolved'?{resolution:resolution.value}:{}),mark_read:markRead});
  if(generation===epoch){notice.value=t('saved');emit('changed');}
}
async function reveal(){
  const generation=epoch;const rows=await request(`/api/inbox/${props.conversation.id}/notes?reveal=true`);
  if(generation===epoch){notes.value=rows;revealed.value=true;}
}
async function save(){
  const generation=epoch;await request(`/api/inbox/${props.conversation.id}/notes`,'POST',{content:note.value});
  if(generation===epoch){note.value='';notice.value=t('saved');notes.value=[];revealed.value=false;}
}
async function reportQuality(){const generation=epoch;await request(`/api/workspace/quality-signals/${props.conversation.id}`,'POST',{category:qualityCategory.value,confirmed:qualityConfirmed.value,event_id:qualityEvent.value});if(generation===epoch){qualityEvent.value=crypto.randomUUID();qualityConfirmed.value=false;notice.value=t('p16QualityRecorded');}}
</script>
<template>
  <article class="operator-queue">
    <h2>{{ t('operatorQueue') }}</h2>
    <p>{{ t('queue_' + (conversation.operator_state || 'not_classified')) }}</p>
    <p>{{ t('queueControlNotice') }}</p>
    <p v-if="conversation.queue_read_at">
{{ t('p16ReviewedAt') }}: {{ date(conversation.queue_read_at,timezone) }}
</p>
    <p v-if="conversation.queue_due_at && conversation.operator_state!=='resolved'">
{{ t('p16Due') }}: {{ date(conversation.queue_due_at,timezone) }} <strong v-if="new Date(conversation.queue_due_at).getTime()<Date.now()">{{ t('p16Overdue') }}</strong>
</p>
    <p v-if="error" role="alert" class="error">
{{ error }}
</p><p v-if="notice" role="status">
{{ notice }}
</p>
    <div class="controls">
<button v-for="state in ['needs_review','assigned','awaiting_customer','resolved']" :key="state" :disabled="busy" @click="run(()=>change(state))">
{{ t(state==='assigned'?'assignToMe':'queue_'+state) }}
</button>
</div>
    <label>{{ t('p16Resolution') }}<select v-model="resolution"><option v-for="value in ['answered','booked','cancelled','escalated','not_required']" :key="value" :value="value">{{ t('p16Resolution_'+value) }}</option></select></label>
    <button :disabled="busy" @click="run(()=>change(conversation.operator_state||'needs_review',false,true))">
{{ t('p16MarkRead') }}
</button>
    <details>
<summary>{{ t('p16QueueSettings') }}</summary><form @submit.prevent="run(()=>change(conversation.operator_state||'needs_review',true))">
<label>{{ t('p16Priority') }}<select v-model="priority"><option v-for="value in ['low','normal','high','urgent']" :key="value" :value="value">{{ t('p16Priority_'+value) }}</option></select></label><label>{{ t('p16Sla') }}<input v-model.number="sla" type="number" min="5" max="10080" required></label><button :disabled="busy">
{{ t('save') }}
</button>
</form>
</details>
    <details>
<summary>{{ t('p16ReportQuality') }}</summary><p>{{ t('p16ReportQualityNotice') }}</p><form @submit.prevent="run(reportQuality)">
<label>{{ t('category') }}<select v-model="qualityCategory"><option v-for="value in ['stt_uncertainty','ambiguous_consent','tool_denial','provider_outage','knowledge_gap','invalid_answer','duplicate_action','abandonment']" :key="value" :value="value">{{ t('p16Signal_'+value) }}</option></select></label><label class="check"><input v-model="qualityConfirmed" type="checkbox" required>{{ t('p16QualityReviewed') }}</label><button :disabled="busy || !qualityConfirmed">
{{ t('save') }}
</button>
</form>
</details>
    <details>
<summary>{{ t('internalNotes') }}</summary>
      <p>{{ t('internalNotePrivacy') }}</p>
      <button :disabled="busy" @click="run(reveal)">
{{ t('revealAuditedNotes') }}
</button>
      <ul v-if="revealed">
<li v-for="item in notes" :key="item.id">
{{ item.content }}
</li>
</ul>
      <p v-if="revealed && !notes.length">
{{ t('empty') }}
</p>
      <form @submit.prevent="run(save)">
<label>{{ t('internalNotes') }}<textarea v-model="note" maxlength="2000" required /></label><button :disabled="busy || !note.trim()">
{{ t('save') }}
</button>
</form>
    </details>
  </article>
</template>
