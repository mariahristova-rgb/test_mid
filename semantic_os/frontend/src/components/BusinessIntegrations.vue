<script setup lang="ts">
import {t} from '../services/i18n';
import ConnectorWorkspace from './ConnectorWorkspace.vue';
import CustomerConnections from './CustomerConnections.vue';
defineProps<{canConfigure:boolean}>();
</script>
<template>
<article class="business-integrations">
<h2>{{ t('connectBusinessTools') }}</h2>
<p>{{ t('integrationCapabilityNotice') }}</p>
<CustomerConnections v-if="canConfigure" />
<details v-if="canConfigure">
<summary>{{ t('ownerIntegrationOnly') }}</summary><RouterLink class="action-link" to="/google">
{{ t('reviewOwnerConnection') }}
</RouterLink>
</details>
<details v-if="canConfigure">
<summary>{{ t('connectorWorkspace') }}</summary><ConnectorWorkspace />
</details>
</article>
</template>
