<script setup lang="ts">
import { computed,onMounted,ref } from 'vue';
import { request } from '../services/api';
import { t,uiLocale,date } from '../services/i18n';
const access=ref<any>({}),assistants=ref<any[]>([]),integrations=ref<any[]>([]),drafts=ref<any[]>([]),current=ref<any>(null),installation=ref<any>(null),proof=ref<any>(null);
const busy=ref(false),error=ref(''),notice=ref(''),website=ref(''),draftId=ref(''),versionId=ref(''),confirmed=ref(false),originToVerify=ref('');
const allowed=computed(()=>access.value.user?.role==='admin');
async function run(action:()=>Promise<unknown>) {if(busy.value)return;busy.value=true;error.value='';notice.value='';try{await action();}catch(e){error.value=e instanceof Error?e.message:t('error');}finally{busy.value=false;}}
async function load(){[access.value,assistants.value]=await Promise.all([request('/api/bootstrap'),request('/api/assistants')]);if(allowed.value)[integrations.value,drafts.value]=await Promise.all([request('/api/widgets'),request('/api/ux/drafts')]);}
function create(){current.value={settings:{assistant_id:assistants.value[0]?.id || '',origins:[],color:'#1d4ed8',logo_url:'',greetings:{'bg-BG':t('widgetGreetingBg'),'en-US':t('widgetGreetingEn')},privacy_notices:{'bg-BG':t('widgetPrivacyBg'),'en-US':t('widgetPrivacyEn')},faq_approved:false,booking_enabled:true,retention_days:Math.min(7,access.value.tenant.retention_days),daily_sessions:100,daily_messages:1000}};website.value='';installation.value=null;proof.value=null;confirmed.value=false;}
async function open(row:any){current.value=JSON.parse(JSON.stringify(row));website.value=row.settings.origins.join('\n');originToVerify.value=row.settings.origins[0];confirmed.value=false;proof.value=null;installation.value=await request(`/api/widgets/${row.id}/installation`);}
async function save(){current.value.settings.origins=website.value.split(/\s+/).filter(Boolean);const result=await request(current.value.id?`/api/widgets/${current.value.id}`:'/api/widgets',current.value.id?'PUT':'POST',current.value.settings);await load();await open(result);notice.value=t('saved');}
async function challenge(){proof.value=await request(`/api/widgets/${current.value.id}/challenge`,'POST',{origin:originToVerify.value});installation.value=await request(`/api/widgets/${current.value.id}/installation`);}
async function verify(){const row=await request(`/api/widgets/${current.value.id}/verify`,'POST',{origin:originToVerify.value});await open(row);notice.value=t('widgetDomainVerified');}
async function publish(){const row=await request(`/api/widgets/${current.value.id}/publish`,'POST',{draft_id:draftId.value,confirmed:confirmed.value});await load();await open(row);notice.value=t('widgetPublished');}
async function action(kind:string){const row=await request(`/api/widgets/${current.value.id}/${kind}`,'POST',{confirmed:confirmed.value,version_id:versionId.value || null});await load();await open(row);notice.value=t('saved');}
async function copy(value:string){await navigator.clipboard.writeText(value);notice.value=t('widgetCopied');}
onMounted(()=>void run(load));
</script>
<template>
  <div class="page-heading">
<h1>{{ t('widgets') }}</h1><RouterLink to="/setup">
{{ t('guidedSetup') }}
</RouterLink>
</div>
  <p class="banner">
{{ t('widgetScopeNotice') }}
</p>
  <p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" role="alert" class="error">
{{ error }}
</p><p v-if="notice" role="status">
{{ notice }}
</p>
  <p v-if="access.user && !allowed">
{{ t('forbidden') }}
</p>
  <template v-if="allowed">
    <article>
<h2>{{ t('widgetIntegrations') }}</h2><button :disabled="busy" @click="create">
{{ t('widgetNew') }}
</button><button v-for="item in integrations" :key="item.id" :disabled="busy" @click="run(()=>open(item))">
{{ item.public_id }} · {{ t(item.state) }}
</button>
</article>
    <template v-if="current">
      <article>
<h2>{{ t('widgetConfigure') }}</h2><form @submit.prevent="run(save)">
<fieldset :disabled="busy || current.state === 'revoked'">
        <label>{{ t('assistant') }}<select v-model="current.settings.assistant_id" :disabled="!!current.id"><option v-for="item in assistants" :key="item.id" :value="item.id">{{ item.name }}</option></select></label>
        <label>{{ t('widgetOrigins') }}<textarea v-model="website" required /></label><p>{{ t('widgetOriginsHelp') }}</p>
        <label>{{ t('widgetColor') }}<input v-model="current.settings.color" type="color"></label><label>{{ t('widgetLogo') }}<input v-model="current.settings.logo_url" type="url"></label>
        <fieldset v-for="locale in ['bg-BG','en-US']" :key="locale">
<legend>{{ t(locale) }}</legend><label>{{ t('greeting') }}<textarea v-model="current.settings.greetings[locale]" required maxlength="1000" /></label><label>{{ t('widgetPrivacy') }}<textarea v-model="current.settings.privacy_notices[locale]" required maxlength="1000" /></label>
</fieldset>
        <label class="check"><input v-model="current.settings.faq_approved" type="checkbox">{{ t('widgetFaqApproval') }}</label><label class="check"><input v-model="current.settings.booking_enabled" type="checkbox">{{ t('widgetBookingEnabled') }}</label>
        <label>{{ t('retentionDays') }}<input v-model.number="current.settings.retention_days" type="number" min="1" :max="Math.min(30,access.tenant.retention_days)" required></label>
        <label>{{ t('widgetDailySessions') }}<input v-model.number="current.settings.daily_sessions" type="number" min="1" max="500" required></label><label>{{ t('widgetDailyMessages') }}<input v-model.number="current.settings.daily_messages" type="number" min="10" max="3000" required></label>
        <p>{{ t('widgetSaveRevokes') }}</p><button>{{ t('save') }}</button>
      </fieldset>
</form>
</article>
      <template v-if="current.id">
        <article>
<h2>{{ t('widgetVerifyDomain') }}</h2><p>{{ t('widgetNonceHelp') }}</p><label>{{ t('widgetOrigins') }}<select v-model="originToVerify" @change="proof=null"><option v-for="site in current.settings.origins" :key="site" :value="site">{{ site }}</option></select></label><button :disabled="busy || current.state === 'revoked'" @click="run(challenge)">
{{ t('widgetCreateChallenge') }}
</button>
          <template v-if="proof">
<p>{{ proof.origin }}{{ proof.path }}</p><label>{{ t('widgetChallengeContent') }}<textarea :value="proof.content" readonly /></label><button :disabled="busy" @click="run(()=>copy(proof.content))">
{{ t('widgetCopyChallenge') }}
</button><p>{{ date(proof.expires_at,access.tenant.timezone) }}</p>
</template>
          <button :disabled="busy || current.state === 'revoked'" @click="run(verify)">
{{ t('widgetVerifyDomain') }}
</button><p v-for="(value,key) in installation?.domains || {}" :key="String(key)">
{{ key }} · {{ t((value as any).state) }}
</p>
        </article>
        <article>
<h2>{{ t('widgetInstall') }}</h2><p>{{ t('widgetInstallHelp') }}</p><label>{{ t('widgetSnippet') }}<textarea :value="installation?.snippet" readonly /></label><button :disabled="busy || !installation" @click="run(()=>copy(installation.snippet))">
{{ t('widgetCopySnippet') }}
</button><p>{{ t('widgetInstallUnverified') }}</p>
</article>
        <article>
<h2>{{ t('widgetPublish') }}</h2><p>{{ t('widgetPublishHelp') }}</p><RouterLink :to="{path:'/setup',query:{assistant:current.settings.assistant_id}}">
{{ t('editDraft') }}
</RouterLink>
          <label>{{ t('widgetPublishedDraft') }}<select v-model="draftId"><option value="">{{ t('selectDraft') }}</option><option v-for="draft in drafts.filter(row=>row.status === 'published' && row.published_assistant_id === current.settings.assistant_id)" :key="draft.id" :value="draft.id">{{ draft.config.name }} · {{ draft.revision }}</option></select></label>
          <label class="check"><input v-model="confirmed" type="checkbox">{{ t('widgetActionConfirmation') }}</label><button :disabled="busy || !confirmed || !draftId || current.state === 'revoked'" @click="run(publish)">
{{ t('widgetPublish') }}
</button>
          <button :disabled="busy || !confirmed || current.state !== 'published'" @click="run(()=>action('unpublish'))">
{{ t('widgetUnpublish') }}
</button><button :disabled="busy || !confirmed || current.state === 'revoked'" @click="run(()=>action('revoke'))">
{{ t('widgetRevoke') }}
</button>
          <label>{{ t('studio_versions') }}<select v-model="versionId"><option value="">{{ t('none') }}</option><option v-for="version in installation?.versions || []" :key="version.id" :value="version.id">{{ date(version.created_at,access.tenant.timezone) }}</option></select></label><button :disabled="busy || !confirmed || !versionId || current.state === 'revoked'" @click="run(()=>action('rollback'))">
{{ t('widgetRollback') }}
</button>
        </article>
      </template>
    </template>
  </template>
</template>
