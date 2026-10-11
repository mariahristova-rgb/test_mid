<script setup lang="ts">
import { onMounted, ref, watch, nextTick, computed } from 'vue';
import { useRoute } from 'vue-router';
import { permittedGroups } from './services/navigation.mjs';
import { t, uiLocale } from './services/i18n';
import { connect, connectDemo, localDemoLogin, signedIn, signOut, signIn, signInGoogle, initialize, authConfigured, googleLoginConfigured, tenantId, request } from './services/api';
const token = ref(''), username = ref('demo'), error = ref(''), busy = ref(false);
const route = useRoute();
const access = ref<any>({});
const navigationOpen=ref(false);
let accessEpoch = 0;
const visibleGroups = computed(() => permittedGroups(access.value.user?.role, access.value.platform_admin));
watch([signedIn,tenantId], async () => { const epoch = ++accessEpoch; access.value = {}; if(signedIn.value) {try { const result = await request('/api/bootstrap'); if(epoch === accessEpoch) access.value = result; } catch { if(epoch === accessEpoch) error.value = t('error'); }} }, {immediate:true});
watch(() => route.path, async () => { navigationOpen.value=false;await nextTick(); document.getElementById('main-content')?.focus(); });
function closeNavigation(){navigationOpen.value=false;void nextTick(()=>document.getElementById('navigation-toggle')?.focus());}
onMounted(async () => {
  if(import.meta.env.VITE_LOCAL_DEMO_LOGIN==='true' && new URLSearchParams(location.search).get('measure')==='local') {
    void import('./services/localPerformance.mjs').then(module=>module.startLocalVitals());
  }
  try { await initialize(); } catch { error.value = t('authError'); }
});
async function login() { busy.value = true; error.value = ''; try { if (localDemoLogin) await connectDemo(username.value, token.value); else await connect(token.value); token.value = ''; } catch { error.value = t('authError'); } finally { busy.value = false; } }
async function googleSignIn(){busy.value=true;error.value='';try{await signInGoogle();}catch{error.value=t('authError');}finally{busy.value=false;}}
watch(uiLocale, async value => { if (signedIn.value) { try { await request('/api/profile', 'PUT', { ui_locale: value }); } catch { error.value = t('error'); } } });
</script>
<template>
  <a class="skip-link" href="#main-content">{{ t('skipToContent') }}</a>
  <header class="topbar">
<strong>{{ t('brand') }}</strong><label>{{ t('language') }}<select v-model="uiLocale" :aria-label="t('language')"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><button v-if="signedIn" @click="signOut">
{{ t('signOut') }}
</button>
</header>
  <div v-if="signedIn" class="mobile-navigation-control">
<button id="navigation-toggle" :aria-expanded="navigationOpen" aria-controls="workspace-navigation" @click="navigationOpen=!navigationOpen">
{{ t(navigationOpen?'p16CloseMenu':'p16OpenMenu') }}
</button>
</div>
  <div v-if="signedIn" class="app-layout">
<nav id="workspace-navigation" :class="{'is-open':navigationOpen}" :aria-label="t('brand')" @keydown.esc="closeNavigation">
<section v-for="group in visibleGroups" :key="group.key" class="navigation-group">
  <h2 v-if="group.key === 'businessWorkspace'">
{{ t(group.key) }}
</h2>
  <details v-if="group.key !== 'businessWorkspace'" :open="group.pages.includes(String(route.meta.page))">
    <summary>{{ t(group.key) }}</summary>
    <RouterLink v-for="page in group.pages" :key="page" :to="'/' + page">
{{ t(page) }}
</RouterLink>
  </details>
  <template v-else>
<RouterLink v-for="page in group.pages" :key="page" :to="'/' + page">
{{ t(page) }}
</RouterLink>
</template>
</section>
</nav><main id="main-content" tabindex="-1">
<p class="context-bar">
{{ t('tenant') }}: {{ access.tenant?.name || tenantId }} · {{ t(access.demo_enabled ? 'demoEnvironment' : 'environment') }}: {{ t(access.environment || 'notRecorded') }}
</p><RouterView :key="tenantId" />
</main>
</div>
  <main v-else id="main-content" class="login" tabindex="-1">
<h1>{{ t('signIn') }}</h1><p>{{ t(googleLoginConfigured?'googleOwnerLoginNotice':localDemoLogin ? 'demoLoginNotice' : 'authUnavailable') }}</p><form v-if="!googleLoginConfigured" @submit.prevent="login">
<label v-if="localDemoLogin">{{ t('username') }}<input v-model="username" required autocomplete="username"></label>
<label v-else>{{ t('tenant') }}<input v-model="tenantId" required autocomplete="organization"></label><label>{{ t(localDemoLogin ? 'password' : 'token') }}<input v-model="token" required type="password" :autocomplete="localDemoLogin ? 'current-password' : 'off'"></label><button :disabled="busy">
{{ t('connect') }}
</button>
</form><button v-if="googleLoginConfigured" :disabled="busy" @click="googleSignIn">
{{ t('signInGoogle') }}
</button><button v-if="authConfigured" @click="signIn">
{{ t('auth0') }}
</button><p v-if="error" role="alert">
{{ error }}
</p>
</main>
</template>
