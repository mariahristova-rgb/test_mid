<script setup lang="ts">
import { onMounted, ref, watch, nextTick, computed } from 'vue';
import { useRoute } from 'vue-router';
import { primaryPages, advancedPages } from './router';
import { t, uiLocale } from './services/i18n';
import { connect, connectDemo, localDemoLogin, signedIn, signOut, signIn, initialize, authConfigured, tenantId, request } from './services/api';
const token = ref(''), username = ref('demo'), error = ref(''), busy = ref(false);
const route = useRoute();
const access = ref<any>({});
let accessEpoch = 0;
const visiblePrimary = computed(() => primaryPages.filter(page => !['testing','operations'].includes(page) || ['admin','operator'].includes(access.value.user?.role)));
const visibleAdvanced = computed(() => advancedPages.filter(page => page === 'administration' ? access.value.platform_admin : ['setup','widgets','google','onboarding','billing'].includes(page) ? access.value.user?.role === 'admin' : true));
watch([signedIn,tenantId], async () => { const epoch = ++accessEpoch; access.value = {}; if(signedIn.value) {try { const result = await request('/api/bootstrap'); if(epoch === accessEpoch) access.value = result; } catch { if(epoch === accessEpoch) error.value = t('error'); }} }, {immediate:true});
watch(() => route.path, async () => { await nextTick(); document.getElementById('main-content')?.focus(); });
onMounted(async () => { try { await initialize(); } catch { error.value = t('authError'); } });
async function login() { busy.value = true; error.value = ''; try { if (localDemoLogin) await connectDemo(username.value, token.value); else await connect(token.value); token.value = ''; } catch { error.value = t('authError'); } finally { busy.value = false; } }
watch(uiLocale, async value => { if (signedIn.value) { try { await request('/api/profile', 'PUT', { ui_locale: value }); } catch { error.value = t('error'); } } });
</script>
<template>
  <a class="skip-link" href="#main-content">{{ t('skipToContent') }}</a>
  <header class="topbar">
<strong>{{ t('brand') }}</strong><label>{{ t('language') }}<select v-model="uiLocale" :aria-label="t('language')"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><button v-if="signedIn" @click="signOut">
{{ t('signOut') }}
</button>
</header>
  <div v-if="signedIn" class="app-layout">
<nav :aria-label="t('brand')">
<RouterLink v-for="page in visiblePrimary" :key="page" :to="'/' + page">
{{ t(page) }}
</RouterLink>
<details>
<summary>{{ t('advanced') }}</summary><RouterLink v-for="page in visibleAdvanced" :key="page" :to="'/' + page">
{{ t(page) }}
</RouterLink>
</details>
</nav><main id="main-content" tabindex="-1">
<p class="context-bar">
{{ t('tenant') }}: {{ tenantId }} · {{ t(access.demo_enabled ? 'demoEnvironment' : 'environment') }}: {{ t(access.environment || 'notRecorded') }}
</p><RouterView :key="tenantId" />
</main>
</div>
  <main v-else id="main-content" class="login" tabindex="-1">
<h1>{{ t('signIn') }}</h1><p>{{ t(localDemoLogin ? 'demoLoginNotice' : 'authUnavailable') }}</p><form @submit.prevent="login">
<label v-if="localDemoLogin">{{ t('username') }}<input v-model="username" required autocomplete="username"></label>
<label v-else>{{ t('tenant') }}<input v-model="tenantId" required autocomplete="organization"></label><label>{{ t(localDemoLogin ? 'password' : 'token') }}<input v-model="token" required type="password" :autocomplete="localDemoLogin ? 'current-password' : 'off'"></label><button :disabled="busy">
{{ t('connect') }}
</button>
</form><button v-if="authConfigured" @click="signIn">
{{ t('auth0') }}
</button><p v-if="error" role="alert">
{{ error }}
</p>
</main>
</template>
