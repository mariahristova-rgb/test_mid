<script setup lang="ts">
import {ref} from 'vue';
import {t} from '../services/i18n';
import ConnectorWorkspace from './ConnectorWorkspace.vue';
const state=ref('disconnected');
const states=['disconnected','connected','reauthorization','degraded'];
const providers=['google','outlook','calendly','hubspot'];
</script>
<template>
<article aria-labelledby="connector-catalog-heading">
<h2 id="connector-catalog-heading">
{{ t('connectorCatalog') }}
</h2>
<p>{{ t('connectorCatalogHelp') }}</p>
<section v-for="provider in providers" :key="provider">
<h3>{{ t('connector_'+provider) }}</h3>
<p>{{ t('connectorComingSoon') }}</p>
<p>{{ t('connectorHelp_'+provider) }}</p>
</section>
<details>
<summary>{{ t('connectorSimulation') }}</summary>
<p>{{ t('connectorSimulationHelp') }}</p>
<label for="connector-demo-state">{{ t('connectorExampleState') }}</label>
<select id="connector-demo-state" v-model="state">
<option v-for="option in states" :key="option" :value="option">
{{ t('connectorState_'+option) }}
</option>
</select>
<p role="status" aria-live="polite" aria-atomic="true">
{{ t('connectorSimulation') }}: {{ t('connectorState_'+state) }}
</p>
</details>
<h3>{{ t('connectorPricing') }}</h3>
<p>{{ t('connectorPricingHelp') }}</p>
<ul>
<li>{{ t('connectorPriceSimple') }}</li>
<li>{{ t('connectorPriceAdvanced') }}</li>
<li>{{ t('connectorPriceEnterprise') }}</li>
</ul>
<ConnectorWorkspace />
</article>
</template>
