import { uiLocale } from './i18n';
import { ref, watch } from 'vue';
import { createAuth0Client, type Auth0Client } from '@auth0/auth0-spa-js';
export const signedIn = ref(false);
export const tenantId = ref(sessionStorage.getItem('assistant-tenant') || 'demo');
let bearer = '';
let client: Auth0Client | undefined;
watch(tenantId, value => { sessionStorage.setItem('assistant-tenant', value); });
const base = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
export const mediaUrl = base.replace(/^http/, 'ws') + '/voice/media';
export const authConfigured = Boolean(import.meta.env.VITE_AUTH0_DOMAIN && import.meta.env.VITE_AUTH0_CLIENT_ID && import.meta.env.VITE_AUTH0_AUDIENCE);
export const localDemoLogin = import.meta.env.VITE_LOCAL_DEMO_LOGIN === 'true' && !authConfigured;
export async function connectDemo(username: string, password: string): Promise<void> {
  const response = await fetch(base + '/api/demo/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-UI-Locale': uiLocale.value }, body: JSON.stringify({ username, password }) });
  if (!response.ok) throw new Error('');
  const session = await response.json();
  tenantId.value = session.tenant_id;
  await connect(session.access_token);
}
export async function request<T = any>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const token = bearer || (client && signedIn.value ? await client.getTokenSilently() : '');
  const response = await fetch(base + path, { method, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'X-Tenant-ID': tenantId.value, 'X-UI-Locale': uiLocale.value }, body: data === undefined ? undefined : JSON.stringify(data) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.message || '');
  return result as T;
}
export async function connect(token: string): Promise<void> { bearer = token; try { await request('/api/bootstrap'); signedIn.value = true; } catch (error) { bearer = ''; throw error; } }
export async function initialize(): Promise<void> {
  if (!authConfigured) return;
  client = await createAuth0Client({ domain: import.meta.env.VITE_AUTH0_DOMAIN, clientId: import.meta.env.VITE_AUTH0_CLIENT_ID, cacheLocation: 'memory', authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE, redirect_uri: window.location.origin } });
  if (new URLSearchParams(location.search).has('code')) { await client.handleRedirectCallback(); history.replaceState({}, '', '/'); }
  signedIn.value = await client.isAuthenticated();
}
export async function signIn(): Promise<void> { await client?.loginWithRedirect(); }
export async function signOut(): Promise<void> { bearer = ''; signedIn.value = false; await client?.logout({ logoutParams: { returnTo: window.location.origin } }); }
