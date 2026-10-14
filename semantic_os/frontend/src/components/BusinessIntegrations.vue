<script setup lang="ts">
import {t} from '../services/i18n';
import ConnectorWorkspace from './ConnectorWorkspace.vue';
defineProps<{canConfigure:boolean}>();
const providers=['google','calendly','hubspot','outlook'];
</script>
<template>
<article class="business-integrations">
<h2>{{ t('connectBusinessTools') }}</h2>
<p>{{ t('integrationCapabilityNotice') }}</p>
<section v-for="provider in providers" :key="provider" class="integration-row">
<div><h3>{{ t('businessProvider_'+provider) }}</h3><p>{{ t('businessProviderHelp_'+provider) }}</p><span class="badge">{{ t(provider==='google'?'ownerIntegrationOnly':'notAvailable') }}</span></div>
<RouterLink v-if="provider==='google' && canConfigure" class="action-link" to="/google">
{{ t('reviewOwnerConnection') }}
</RouterLink>
<button v-else disabled>
{{ t('notAvailable') }}
</button>
</section>
<ConnectorWorkspace v-if="canConfigure" />
</article>
</template>
