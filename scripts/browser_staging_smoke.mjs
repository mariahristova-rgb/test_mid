// Local TLS staging smoke; independent Python verification checks the certificate chain.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const session = JSON.parse(readFileSync('artifacts/staging/session.json', 'utf8'));
assert.equal(session.origin, 'https://127.0.0.1:8443');
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const page = await browser.newPage({ ignoreHTTPSErrors: true });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
try {
  await page.goto(session.origin);
  await page.getByLabel('Organization').fill('staging');
  await page.getByLabel('Development access token').fill(session.token);
  await page.getByRole('button', { name: 'Connect', exact: true }).click();
  await page.getByRole('heading', { name: 'Dashboard', exact: true }).waitFor();
  await page.getByRole('link', { name: 'Billing', exact: true }).click();
  await page.getByRole('heading', { name: 'Subscription status', exact: true }).waitFor();
  await page.getByLabel('Interface language', { exact: true }).selectOption('bg-BG');
  await page.getByRole('heading', { name: 'Плащания', exact: true }).waitFor();
  await page.screenshot({ path: 'artifacts/staging-billing-bg.png', fullPage: true });
  assert.deepEqual(errors, []);
  console.log('Local HTTPS staging browser passed: signed identity session, billing and Bulgarian interface.');
} finally { await browser.close(); }
