import { uiLocale, t } from './i18n';
import { ref, watch } from 'vue';
import { createAuth0Client, type Auth0Client } from '@auth0/auth0-spa-js';
export const signedIn = ref(false);
const requestedTenant = new URLSearchParams(window.location.search).get('tenant');
const tenantFromLink = requestedTenant && /^[a-zA-Z0-9_-]{1,100}$/.test(requestedTenant) ? requestedTenant : null;
export const tenantId = ref(tenantFromLink || sessionStorage.getItem('assistant-tenant') || 'demo');
if (tenantFromLink) sessionStorage.setItem('assistant-tenant', tenantFromLink);
let bearer = '';
let client: Auth0Client | undefined;
watch(tenantId, value => { sessionStorage.setItem('assistant-tenant', value); });
const base = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
export const mediaUrl = base.replace(/^http/, 'ws') + '/voice/media';
export const authConfigured = Boolean(import.meta.env.VITE_AUTH0_DOMAIN && import.meta.env.VITE_AUTH0_CLIENT_ID && import.meta.env.VITE_AUTH0_AUDIENCE);
export const googleLoginConfigured = import.meta.env.VITE_GOOGLE_LOGIN === 'true';
export const localDemoLogin = import.meta.env.VITE_LOCAL_DEMO_LOGIN === 'true' && !authConfigured && !googleLoginConfigured;
export class ApiError extends Error {
  constructor(public code:string, public status:number) {super(t(code) !== code ? t(code) : t('error'));}
}
export async function connectDemo(username: string, password: string): Promise<void> {
  const response = await fetch(base + '/api/demo/login', { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-UI-Locale': uiLocale.value }, body: JSON.stringify({ username, password }) });
  if (!response.ok) throw new Error('');
  const session = await response.json();
  const selectedTenant = sessionStorage.getItem('assistant-tenant');
  tenantId.value = selectedTenant || session.tenant_id;
  try {
    await connect(session.access_token);
  } catch (error) {
    if (!selectedTenant || !(error instanceof ApiError) || ![403,404].includes(error.status)) throw error;
    tenantId.value = session.tenant_id;
    await connect(session.access_token);
  }
}
export async function request<T = any>(path: string, method = 'GET', data?: unknown, signal?: AbortSignal): Promise<T> {
  try {
  const requestTenant = tenantId.value, requestLocale = uiLocale.value;
  const token = bearer || (client && signedIn.value ? await client.getTokenSilently() : '');
  if(requestTenant!==tenantId.value)throw new DOMException(t('p16TenantChanged'),'AbortError');
  const response = await fetch(base + path, { method, signal, headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json', 'X-Tenant-ID': requestTenant, 'X-UI-Locale': requestLocale }, body: data === undefined ? undefined : JSON.stringify(data) });
  const result = await response.json();
  if(requestTenant!==tenantId.value)throw new DOMException(t('p16TenantChanged'),'AbortError');
  if (!response.ok) throw new ApiError(result.code || 'error',response.status);
  return result as T;
  } catch(error) {
    if(error instanceof ApiError || error instanceof Error && error.name === 'AbortError') throw error;
    throw new Error(t('connectionUnavailable'));
  }
}
export async function connect(token: string): Promise<void> { bearer = token; try { await request('/api/bootstrap'); signedIn.value = true; } catch (error) { bearer = ''; throw error; } }
export async function initialize(): Promise<void> {
  if (googleLoginConfigured) {
    const parameters=new URLSearchParams(location.search);
    if(parameters.get('owner_error')==='true'){
      parameters.delete('owner_error');history.replaceState({},'',location.pathname+(parameters.size?'?'+parameters.toString():''));
      throw new ApiError('authError',403);
    }
    const ticket=new URLSearchParams(location.hash.slice(1)).get('owner_ticket');
    if(ticket){
      history.replaceState({},'',location.pathname+location.search);
      const response=await fetch(base+'/api/auth/google/redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({ticket})});
      if(!response.ok)throw new ApiError('authError',response.status);
      const session=await response.json();tenantId.value=session.tenant_id;await connect(session.access_token);
    }
    return;
  }
  if (!authConfigured) return;
  client = await createAuth0Client({ domain: import.meta.env.VITE_AUTH0_DOMAIN, clientId: import.meta.env.VITE_AUTH0_CLIENT_ID, cacheLocation: 'memory', authorizationParams: { audience: import.meta.env.VITE_AUTH0_AUDIENCE, redirect_uri: window.location.origin } });
  if (new URLSearchParams(location.search).has('code')) { await client.handleRedirectCallback(); history.replaceState({}, '', '/'); }
  signedIn.value = await client.isAuthenticated();
}
export async function signInGoogle():Promise<void>{
  const response=await fetch(base+'/api/auth/google/start',{method:'POST',headers:{'X-UI-Locale':uiLocale.value}});
  if(!response.ok)throw new ApiError('authError',response.status);
  const result=await response.json();const target=new URL(result.authorize_url);
  if(target.origin!=='https://accounts.google.com')throw new ApiError('authError',401);
  window.location.assign(target.href);
}
export async function signIn(): Promise<void> { await client?.loginWithRedirect(); }
export async function signOut(): Promise<void> { bearer = ''; signedIn.value = false; await client?.logout({ logoutParams: { returnTo: window.location.origin } }); }
