// Build an origin-specific CSP; build arguments are public configuration, never secrets.
import { writeFileSync } from 'node:fs';
const auth = process.env.VITE_AUTH0_DOMAIN;
if (!/^[a-z0-9.-]+$/i.test(auth || '')) throw new Error('A DNS identity domain is required');
const base = process.env.VITE_API_URL || '';
let sources = "'self'";
if (base.startsWith('/') && (!/^\/[a-z0-9/_-]*$/i.test(base) || base.startsWith('//'))) throw new Error('Invalid same-origin API prefix');
if (base && !base.startsWith('/')) {
  const url = new URL(base);
  if (url.username || url.password || url.search || url.hash || !['https:', 'http:'].includes(url.protocol)) throw new Error('Invalid API origin');
  if (url.protocol === 'http:' && !['127.0.0.1', 'localhost'].includes(url.hostname)) throw new Error('Public APIs require HTTPS');
  sources += ` ${url.origin} ${url.origin.replace(/^http/, 'ws')}`;
}
const policy = `default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src ${sources} https://${auth}; frame-src https://${auth}; object-src 'none'; base-uri 'self'; frame-ancestors 'none'`;
writeFileSync('nginx.production.conf', `server {
  listen 8080;
  server_tokens off;
  root /usr/share/nginx/html;
  index index.html;
  add_header X-Content-Type-Options nosniff always;
  add_header Referrer-Policy no-referrer always;
  add_header X-Frame-Options DENY always;
  add_header Content-Security-Policy "${policy}" always;
  location / { try_files $uri $uri/ /index.html; }
}
`);
