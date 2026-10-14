<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue';
import { request, tenantId } from '../services/api';
import { t, number, uiLocale } from '../services/i18n';
import {measuredQuantity} from '../services/usage.mjs';
const period=ref(new Date().toISOString().slice(0,7)),state=ref<any>(null),busy=ref(false),error=ref('');
const assistant=ref(''),channel=ref(''),provider=ref('');
const options=(key:string)=>[...new Set<string>((state.value?.groups||[]).map((row:any)=>row[key]).filter(Boolean))];
const filtered=computed(()=>(state.value?.groups||[]).filter((row:any)=>(!assistant.value||row.assistant_id===assistant.value)&&(!channel.value||row.channel===channel.value)&&(!provider.value||row.provider===provider.value)));
let epoch=0;
async function load(){const generation=++epoch;busy.value=true;error.value='';state.value=null;
  assistant.value='';channel.value='';provider.value='';
  try{const result=await request('/api/workspace/usage?period='+encodeURIComponent(period.value));if(generation===epoch)state.value=result;}
  catch(e){if(generation===epoch)error.value=e instanceof Error?e.message:t('error');}finally{if(generation===epoch)busy.value=false;}}
onMounted(()=>void load());watch(tenantId,()=>void load());onUnmounted(()=>epoch++);
</script>
<template>
  <article>
<h2>{{ t('p16UsageHistory') }}</h2><form class="controls" @submit.prevent="load">
<label>{{ t('billingPeriod') }}<input v-model="period" type="month" required></label><button :disabled="busy">
{{ t('refresh') }}
</button>
</form><p v-if="busy" role="status">
{{ t('busy') }}
</p><p v-if="error" role="alert" class="error">
{{ error }}
</p><p>{{ t('p16CostsNotice') }}</p>
    <template v-if="state">
      <div class="controls">
<label>{{ t('assistant') }}<select v-model="assistant"><option value="">{{ t('all') }}</option><option v-for="id in options('assistant_id')" :key="id" :value="id">{{ id }}</option></select></label><label>{{ t('channel') }}<select v-model="channel"><option value="">{{ t('all') }}</option><option v-for="id in options('channel')" :key="id" :value="id">{{ t(id) }}</option></select></label><label>{{ t('provider') }}<select v-model="provider"><option value="">{{ t('all') }}</option><option v-for="id in options('provider')" :key="id" :value="id">{{ id }}</option></select></label>
</div>
<p v-if="state.truncated">
{{ t('p16BoundedNotice') }}
</p><p v-if="!state.groups.length">
{{ t('p16NoUsage') }}
</p><div class="table-wrap">
<table>
<caption>{{ t('p16UsageHistory') }} · {{ t('UTC') }}</caption><thead>
<tr>
<th scope="col">
{{ t('p16UsageDay') }}
</th><th scope="col">
{{ t('category') }}
</th><th scope="col">
{{ t('provider') }}
</th><th scope="col">
{{ t('quantity') }}
</th><th scope="col">
{{ t('unit') }}
</th>
<th scope="col">
{{ t('assistant') }}
</th><th scope="col">
{{ t('channel') }}
</th>
</tr>
</thead><tbody>
<tr v-for="(row,index) in filtered" :key="index">
<td>{{ row.day }}</td><td>{{ t(row.category) }}</td><td>{{ row.provider }}</td><td>{{ measuredQuantity(row.quantity_text,row.unit,uiLocale) }}</td><td>{{ t(row.unit==='millisecond'?'second':row.unit) }}</td><td>{{ row.assistant_id||t('p16NotAllocated') }}</td><td>{{ row.channel?t(row.channel):t('p16NotAllocated') }}</td>
</tr>
</tbody>
</table>
</div><p>{{ t('p16DimensionsUnavailable') }}</p><ul>
<li v-for="(warning,index) in state.current?.warnings || []" :key="index">
{{ t(warning.category) }} · {{ number(warning.threshold_percent || 80) }}% · {{ t('usage_warning') }}
</li>
</ul>
<details v-if="state.forecast?.length">
<summary>{{ t('p16UsageForecast') }}</summary><p>{{ t('p16ForecastNotice') }}</p><p v-for="row in state.forecast" :key="row.category">
{{ t(row.category) }}: {{ measuredQuantity(row.estimated_month_quantity_text,row.unit,uiLocale) }} {{ t(row.unit==='millisecond'?'second':row.unit) }}
</p>
</details>
</template>
  </article>
</template>
