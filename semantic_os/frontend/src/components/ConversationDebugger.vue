<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue';
import { request } from '../services/api';
import { t, date, number } from '../services/i18n';
const props = defineProps<{conversationId:string; timezone:string}>();
const data = ref<any>(null), error = ref(''), busy = ref(false), panel = ref('outcome');
let controller: AbortController | undefined, epoch = 0;
async function load() {
  const identity = props.conversationId;
  controller?.abort(); controller = new AbortController(); const generation = ++epoch;
  data.value = null; error.value = ''; busy.value = true;
  try { const result = await request(`/api/ux/conversations/${identity}/diagnostics`,'GET',undefined,controller.signal); if(generation === epoch) data.value = result; }
  catch(e) { if(generation === epoch && !controller.signal.aborted) error.value = e instanceof Error ? e.message : t('error'); }
  finally { if(generation === epoch) busy.value = false; }
}
watch(() => props.conversationId, load, {immediate:true});
onUnmounted(() => {epoch++; controller?.abort();});
</script>
<template>
  <article class="debugger">
<h2>{{ t('conversationDebugger') }}</h2>
<p>{{ t('diagnosticSnapshotNotice') }}</p><button :disabled="busy" @click="load">
{{ t('refresh') }}
</button>
    <p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" role="alert" class="error">
{{ error }}
</p>
    <template v-if="data">
      <p>{{ t(data.channel) }} · {{ t(data.locale || 'notRecorded') }} · {{ t(data.human_escalation ? 'aiPaused' : 'aiActive') }}</p>
      <p class="banner">
{{ t('transcriptPrivacy') }}
</p>
      <div class="debugger-switch controls">
<button v-for="key in ['conversation','outcome','diagnostics']" :key="key" :aria-pressed="panel === key" @click="panel = key">
{{ t('debug_' + key) }}
</button>
</div>
      <div class="diagnostic-grid">
        <section :class="{ 'mobile-hidden':panel !== 'conversation' }">
<h3>{{ t('debug_conversation') }}</h3>
          <RouterLink :to="{path:'/inbox',query:{conversation:conversationId}}">
{{ t('openConversation') }}
</RouterLink>
          <p v-for="message in data.message_metadata" :key="message.id">
{{ t(message.direction) }} · {{ date(message.timestamp,timezone) }} · {{ t(message.locale) }} · {{ t(message.delivery_status || 'notRecorded') }}
</p>
          <p v-if="!data.message_metadata.length">
{{ t('notRecorded') }}
</p>
        </section>
        <section :class="{ 'mobile-hidden':panel !== 'outcome' }">
<h3>{{ t('debug_outcome') }}</h3>
          <p>{{ t(data.booking_status || 'notRecorded') }}</p><p v-if="!data.appointments.length">
{{ t('noPersistedBooking') }}
</p>
          <p v-for="booking in data.appointments" :key="booking.id">
<RouterLink :to="{path:'/appointments',query:{conversation:conversationId}}">
{{ t('appointments') }} · {{ date(booking.starts_at,booking.timezone || timezone) }}
</RouterLink> · {{ t(booking.status) }}
</p>
          <ol class="timeline">
<li v-for="event in data.timeline" :key="event.kind + event.id">
<strong>{{ t('event_' + event.kind) }}</strong><p>{{ t(event.tool || event.source || 'status') }} · {{ t(event.code || event.status || 'notRecorded') }}</p>
            <details><summary>{{ t('technicalDetails') }}</summary><p>{{ t('id') }}: {{ event.id }}</p><p>{{ t('correlationId') }}: {{ event.correlation_id || t('notRecorded') }}</p><p>{{ event.timestamp ? date(event.timestamp,timezone) : t('timestampNotRecorded') }}</p></details>
          </li>
</ol>
        </section>
        <section :class="{ 'mobile-hidden':panel !== 'diagnostics' }">
<h3>{{ t('debug_diagnostics') }}</h3>
          <p>{{ t(data.voice_coverage === 'not_applicable' ? 'notApplicable' : data.voice_coverage === 'not_recorded' ? 'notRecorded' : 'recorded') }}</p><p>{{ t('traceMemoryNotice') }}</p>
          <p v-for="(trace,index) in data.voice_trace" :key="index">
{{ t('trace_' + trace.stage) }} · {{ trace.duration_ms == null ? t('durationNotRecorded') : number(trace.duration_ms) + ' ' + t('milliseconds') }}<br>{{ t('correlationId') }}: {{ trace.correlation_id }}
</p>
          <p>{{ t('voice_acceptance_blocked') }}</p>
          <details>
<summary>{{ t('stageCoverage') }}</summary><p v-for="stage in data.stage_coverage" :key="stage.stage">
{{ t('trace_' + stage.stage) }} · {{ t(stage.coverage === 'not_applicable' ? 'notApplicable' : stage.coverage === 'not_recorded' ? 'notRecorded' : 'recorded') }}
</p>
</details>
          <RouterLink :to="{path:'/testing',query:{scenario:data.suggested_scenario}}">
{{ t('reproduceSyntheticScenario') }}
</RouterLink><p>{{ t('syntheticReplayNotice') }}</p>
        </section>
      </div>
    </template>
  </article>
</template>
