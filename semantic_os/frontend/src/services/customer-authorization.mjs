/** Validate the server-produced provider URL before leaving the business workspace. */
export function customerAuthorizationURL(value, provider) {
  const endpoints = {
    google: ['accounts.google.com', '/o/oauth2/v2/auth'],
    outlook: ['login.microsoftonline.com', '/common/oauth2/v2.0/authorize'],
    calendly: ['auth.calendly.com', '/oauth/authorize'],
    hubspot: ['app.hubspot.com', '/oauth/authorize'],
  };
  const endpoint = endpoints[provider];
  const url = new URL(value);
  if (!endpoint || url.protocol !== 'https:' || url.hostname !== endpoint[0] || url.pathname !== endpoint[1]
      || url.username || url.password || url.hash || (url.port && url.port !== '443')
      || !url.searchParams.get('state') || !url.searchParams.get('client_id')
      || url.searchParams.get('response_type') !== 'code') throw new Error('Invalid authorization URL');
  const callback = new URL(url.searchParams.get('redirect_uri'));
  if (callback.protocol !== 'https:' || callback.username || callback.password || callback.hash || callback.search
      || callback.pathname !== '/backend/api/connectors/oauth/' + provider + '/callback') throw new Error('Invalid callback');
  return url.href;
}
