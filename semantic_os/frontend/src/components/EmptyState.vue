<template>
  <div class="flex min-h-36 flex-col items-center justify-center rounded-2xl border border-dashed border-slate-300 bg-white px-6 py-8 text-center">
    <component :is="icon" v-if="icon" class="h-7 w-7 text-slate-400" aria-hidden="true" />
    <h3 class="mt-2 text-sm font-semibold text-slate-900">
{{ title }}
</h3>
    <p v-if="description" class="mt-1 max-w-md text-sm leading-6 text-slate-500">
{{ description }}
</p>
    <button v-if="actionLabel" type="button" class="mt-4 rounded-xl bg-slate-950 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800" @click="$emit('action')">
      {{ actionLabel }}
    </button>
  </div>
</template>

<script setup lang="ts">
import type { Component } from "vue";

defineProps<{ title: string; description?: string; actionLabel?: string; icon?: Component }>();
defineEmits<{ action: [] }>();
</script>
