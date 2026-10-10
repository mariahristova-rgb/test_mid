import { createRouter, createWebHistory } from 'vue-router';
import WorkspaceView from '../views/WorkspaceView.vue';
import SaaSView from '../views/SaaSView.vue';
const saasPages = ['onboarding', 'billing', 'usage', 'operations', 'administration'];
export const pages = ['dashboard', 'assistants', 'agents', 'inbox', 'calls', 'channels', 'appointments', 'integrations', 'settings', ...saasPages];
export default createRouter({ history: createWebHistory(), routes: [
  { path: '/', redirect: '/dashboard' }, ...pages.map(page => ({ path: '/' + page, component: saasPages.includes(page) ? SaaSView : WorkspaceView, meta: { page } })),
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
] });
