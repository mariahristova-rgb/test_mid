<script setup lang="ts">
import { ref, computed, useId, nextTick } from 'vue';
import { request } from '../services/api';
import { t, date, number } from '../services/i18n';
const props = defineProps<{assistant:any; canConfigure:boolean; timezone:string}>();
const selected = ref('overview'), summary = ref<any>(null), error = ref('');
const identity = useId();
const tabs = computed(() => ['overview','instructions',...(props.assistant.faq_entries?.length ? ['knowledge'] : []),'tools','channels','voice','testing','versions','activity']);
async function choose(key: string) {
  selected.value = key; error.value = '';
  if(['versions','activity'].includes(key) && !summary.value) {
    try {summary.value = await request(`/api/ux/assistants/${props.assistant.id}/summary`);} catch(e) {error.value = e instanceof Error ? e.message : t('error');}
  }
}
async function navigate(event: KeyboardEvent) {
  const index = tabs.value.indexOf(selected.value);
  const target = event.key === 'ArrowRight' ? (index+1)%tabs.value.length : event.key === 'ArrowLeft' ? (index+tabs.value.length-1)%tabs.value.length : event.key === 'Home' ? 0 : event.key === 'End' ? tabs.value.length-1 : -1;
  if(target<0) return; event.preventDefault(); void choose(tabs.value[target]); await nextTick(); document.getElementById(identity+'-'+tabs.value[target])?.focus();
}
</script>
<template>
  <section class="assistant-studio">
    <div class="studio-tabs" role="tablist" :aria-label="t('assistantStudio')" @keydown="navigate">
      <button
v-for="key in tabs"
:id="identity + '-' + key"
:key="key"
type="button"
role="tab"
:aria-selected="selected === key"
:aria-controls="identity + '-panel'"
:tabindex="selected === key ? 0 : -1"
@click="choose(key)"
>
{{ t('studio_' + key) }}
</button>
    </div>
    <div :id="identity + '-panel'" role="tabpanel" :aria-labelledby="identity + '-' + selected" tabindex="0">
      <p v-if="error" role="alert" class="error">
{{ error }}
</p>
      <template v-if="selected === 'overview'">
<p>{{ assistant.description || t('noDescription') }}</p><p>{{ t(assistant.status) }} · {{ t(assistant.default_locale) }}</p><p>{{ t('voice_acceptance_blocked') }}</p>
</template>
      <template v-if="selected === 'instructions'">
<p class="bubble">
{{ assistant.instructions || t('noInstructions') }}
</p>
</template>
      <template v-if="selected === 'knowledge'">
<p>{{ t('faqKnowledgeScope') }}</p><dl v-for="(entry,index) in assistant.faq_entries" :key="index">
<dt>{{ entry.question_bg }}</dt><dd>{{ entry.answer_bg }}</dd><dt>{{ entry.question_en }}</dt><dd>{{ entry.answer_en }}</dd>
</dl>
</template>
      <template v-if="selected === 'tools'">
<p>{{ t('twoAgentHelp') }}</p><p v-for="tool in assistant.allowed_tools" :key="tool">
{{ t(tool) }}
</p><p>{{ t('permissionIntersection') }}</p><RouterLink to="/agents">
{{ t('agents') }}
</RouterLink>
</template>
      <template v-if="selected === 'channels'">
<p v-for="channel in assistant.enabled_channels" :key="channel">
{{ t(channel) }}
</p><p>{{ t('providerStatusScope') }}</p><RouterLink to="/integrations">
{{ t('integrations') }}
</RouterLink>
</template>
      <template v-if="selected === 'voice'">
<p>{{ t('bothLocalesRequired') }}</p><dl><dt>{{ t('callLanguage') }}</dt><dd>{{ t(assistant.voice_settings.locale) }}</dd><dt>{{ t('telephonyProvider') }}</dt><dd>{{ t(assistant.voice_settings.telephony_provider === 'mock' ? 'MOCK_ONLY' : assistant.voice_settings.telephony_provider) }}</dd><dt>{{ t('sttProvider') }}</dt><dd>{{ t(assistant.voice_settings.stt_provider === 'mock' ? 'MOCK_ONLY' : assistant.voice_settings.stt_provider) }}</dd><dt>{{ t('ttsProvider') }}</dt><dd>{{ t(assistant.voice_settings.tts_provider === 'mock' ? 'MOCK_ONLY' : assistant.voice_settings.tts_provider) }}</dd></dl><p>{{ t('providerPreserved') }}</p>
</template>
      <template v-if="selected === 'testing'">
<p>{{ t('isolatedStudioNotice') }}</p><RouterLink to="/testing">
{{ t('testAssistant') }}
</RouterLink>
</template>
      <template v-if="selected === 'versions'">
<p>{{ t('versionScope') }}</p><p v-if="summary && !summary.versions.length">
{{ t('noRecordedVersions') }}
</p><p v-for="version in summary?.versions || []" :key="version.id">
{{ date(version.timestamp,timezone) }} · {{ t('revision') }} {{ number(version.revision) }}
</p>
</template>
      <template v-if="selected === 'activity'">
<p>{{ t('countsNotSuccessRates') }}</p><p v-if="summary">
{{ t('inbox') }}: {{ number(summary.counts.conversations) }} · {{ t('calls') }}: {{ number(summary.counts.call_sessions) }}
</p><RouterLink to="/calls">
{{ t('calls') }}
</RouterLink>
</template>
      <RouterLink v-if="canConfigure" class="action-link" :to="{path:'/setup',query:{assistant:assistant.id}}">
{{ t('editDraft') }}
</RouterLink>
    </div>
  </section>
</template>
