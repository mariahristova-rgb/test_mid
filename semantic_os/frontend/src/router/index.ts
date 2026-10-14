import { createRouter, createWebHistory } from 'vue-router';
const WorkspaceView = () => import('../views/WorkspaceView.vue');
const SaaSView = () => import('../views/SaaSView.vue');
const SetupView = () => import('../views/SetupView.vue');
const WidgetView = () => import('../views/WidgetView.vue');
const GoogleWorkspaceView = () => import('../views/GoogleWorkspaceView.vue');
const CustomerWorkspaceView = () => import('../views/CustomerWorkspaceView.vue');
const customerPages=['progress','health','quality','analytics','leads'];
const saasPages = ['onboarding', 'billing', 'usage', 'operations', 'administration'];
export const pages = ['dashboard', 'assistants', 'inbox', 'testing', 'calls', 'appointments', 'operations', 'integrations', 'settings', 'team', 'setup', 'widgets','google', 'agents', 'channels', 'onboarding', 'billing', 'usage', 'administration',...customerPages];
export const primaryPages = ['dashboard', 'assistants', 'inbox', 'testing', 'calls', 'appointments', 'operations', 'integrations', 'settings'];
export const advancedPages = pages.filter(page => !primaryPages.includes(page));
export default createRouter({ history: createWebHistory(), routes: [
  { path: '/', redirect: '/dashboard' }, ...pages.map(page => ({ path: '/' + page, component: customerPages.includes(page)?CustomerWorkspaceView:page==='google'?GoogleWorkspaceView:page === 'widgets' ? WidgetView : ['setup','testing'].includes(page) ? SetupView : saasPages.includes(page) ? SaaSView : WorkspaceView, meta: { page } })),
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
] });
