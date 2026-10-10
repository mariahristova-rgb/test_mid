import { ref, watch } from 'vue';
import en from '../locales/en-US.json';
import bg from '../locales/bg-BG.json';
export type Locale = 'bg-BG' | 'en-US';
const saved = localStorage.getItem('assistant-ui-locale');
export const uiLocale = ref<Locale>(saved === 'bg-BG' ? 'bg-BG' : 'en-US');
const resources: Record<Locale, Record<string, string>> = { 'en-US': en, 'bg-BG': bg };
export function t(key: string): string { return resources[uiLocale.value][key] ?? key; }
watch(uiLocale, value => { localStorage.setItem('assistant-ui-locale', value); document.documentElement.lang = value; document.title = resources[value].brand; }, { immediate: true });
export function date(value: string, timezone = 'Europe/Sofia'): string { return new Intl.DateTimeFormat(uiLocale.value, { timeZone: timezone, dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)); }
export function number(value: number): string { return new Intl.NumberFormat(uiLocale.value).format(value); }
export function currency(value: number, code: string): string { return new Intl.NumberFormat(uiLocale.value, { style: 'currency', currency: code }).format(value); }
