<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { request } from '../services/api';
import { t } from '../services/i18n';
const props=defineProps<{conversation:any;userId:string}>();
const emit=defineEmits<{changed:[]}>();
const note=ref(''),notes=ref<any[]>([]),error=ref(''),notice=ref(''),busy=ref(false),revealed=ref(false);
let epoch=0;
watch(()=>props.conversation.id,()=>{epoch++;note.value='';notes.value=[];revealed.value=false;error.value='';notice.value='';busy.value=false;});
onUnmounted(()=>epoch++);
async function run(action:()=>Promise<void>){
  if(busy.value)return;const generation=epoch;busy.value=true;error.value='';notice.value='';
  try{await action();}catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}
  finally{if(generation===epoch)busy.value=false;}
}
async function change(state:string){
  const generation=epoch;
  await request(`/api/inbox/${props.conversation.id}/queue`,'PUT',{revision:props.conversation.queue_revision||0,state,assigned_user_id:state==='assigned'?props.userId:null});
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
</script>
<template>
  <article class="operator-queue">
    <h2>{{ t('operatorQueue') }}</h2>
    <p>{{ t('queue_' + (conversation.operator_state || 'not_classified')) }}</p>
    <p>{{ t('queueControlNotice') }}</p>
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
