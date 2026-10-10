<script setup lang="ts">
import { onMounted, ref, watch } from 'vue';
import { pages } from './router';
import { t, uiLocale } from './services/i18n';
import { connect, connectDemo, localDemoLogin, signedIn, signOut, signIn, initialize, authConfigured, tenantId, request } from './services/api';
const token = ref(''), username = ref('demo'), error = ref(''), busy = ref(false);
onMounted(async () => { try { await initialize(); } catch { error.value = t('authError'); } });
async function login() { busy.value = true; error.value = ''; try { if (localDemoLogin) await connectDemo(username.value, token.value); else await connect(token.value); token.value = ''; } catch { error.value = t('authError'); } finally { busy.value = false; } }
watch(uiLocale, async value => { if (signedIn.value) { try { await request('/api/profile', 'PUT', { ui_locale: value }); } catch { error.value = t('error'); } } });
</script>
<template>
  <header class="topbar">
<strong>{{ t('brand') }}</strong><label>{{ t('language') }}<select v-model="uiLocale" :aria-label="t('language')"><option value="bg-BG">{{ t('bg-BG') }}</option><option value="en-US">{{ t('en-US') }}</option></select></label><button v-if="signedIn" @click="signOut">
{{ t('signOut') }}
</button>
</header>
  <div v-if="signedIn" class="app-layout">
<nav :aria-label="t('brand')">
<RouterLink v-for="page in pages" :key="page" :to="'/' + page">
{{ t(page) }}
</RouterLink>
</nav><main><RouterView :key="tenantId" /></main>
</div>
  <main v-else class="login">
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
