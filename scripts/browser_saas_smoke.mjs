// Bilingual SaaS user flows in an explicitly local mock preview.
import assert from 'node:assert/strict';
import { readFileSync, mkdirSync } from 'node:fs';
import { createRequire } from 'node:module';
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
const origin = 'http://127.0.0.1:3011', api = 'http://127.0.0.1:8011';
const labels = Object.fromEntries(['en-US', 'bg-BG'].map(locale => [locale, JSON.parse(readFileSync(`semantic_os/frontend/src/locales/${locale}.json`, 'utf8'))]));
const adminHeaders = { Authorization: 'Bearer synthetic-review-session', 'Content-Type': 'application/json', 'X-Tenant-ID': 'demo' };
const result = await fetch(api + '/api/platform/plans', { method: 'PUT', headers: adminHeaders, body: JSON.stringify({
  id: 'browser-fixture', name_en: 'Browser fixture', name_bg: 'Тестов план за браузъра', monthly_minor: 1201, annual_minor: 12001,
  trial_days: 2, limits: { ai_messages: { maximum: 2 } }
}) });
assert.equal(result.status, 200);
const browser = await chromium.launch({ channel: 'msedge', headless: true });
const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
const errors = [];
page.on('pageerror', error => errors.push(error.message));
await page.route('**/*', route => new URL(route.request().url()).hostname === '127.0.0.1' ? route.continue() : route.abort());
mkdirSync('artifacts', { recursive: true });
try {
  await page.goto(origin);
  await page.getByLabel(labels['en-US'].token, { exact: true }).fill('synthetic-review-session');
  await page.getByRole('button', { name: labels['en-US'].connect, exact: true }).click();
  await page.getByRole('heading', { name: labels['en-US'].dashboard, exact: true }).waitFor();
  for (const locale of ['bg-BG', 'en-US']) {
    const prior = locale === 'bg-BG' ? 'en-US' : 'bg-BG';
    await page.getByLabel(labels[prior].language, { exact: true }).selectOption(locale);
    const t = key => labels[locale][key];
    await page.getByRole('link', { name: t('onboarding'), exact: true }).click();
    await page.getByLabel(t('organizationName'), { exact: true }).fill('Synthetic browser organization ' + locale);
    await page.getByLabel(t('administratorEmail'), { exact: true }).fill('browser@example.invalid');
    await page.getByLabel(t('defaultLanguage'), { exact: true }).selectOption(locale);
    await page.getByLabel(t('subscriptionPlan'), { exact: true }).first().selectOption('browser-fixture');
    await page.getByRole('button', { name: t('registerOrganization'), exact: true }).click();
    await page.getByRole('button', { name: t('readMockVerification'), exact: true }).waitFor();
    await page.getByRole('button', { name: t('readMockVerification'), exact: true }).click();
    await page.getByRole('button', { name: t('verifyEmail'), exact: true }).click();
    await page.getByText(t('emailVerified'), { exact: true }).waitFor();
    await page.getByRole('button', { name: t('startTrial'), exact: true }).click();
    await page.locator('.page-heading button:not([disabled])').waitFor();
    await page.getByRole('link', { name: t('billing'), exact: true }).first().click();
    await page.getByRole('button', { name: t('prepareCheckout'), exact: true }).click();
    await page.getByRole('button', { name: t('simulatePayment'), exact: true }).waitFor();
    await page.getByRole('button', { name: t('simulatePayment'), exact: true }).click();
    await page.getByRole('cell', { name: t('paid'), exact: true }).waitFor();
    const invoiceText = await page.locator('table').first().innerText();
    assert.match(invoiceText, locale === 'bg-BG' ? /12,01/ : /12\.01/);
    await page.screenshot({ path: `artifacts/billing-${locale}.png`, fullPage: true });
    await page.getByRole('link', { name: t('usage'), exact: true }).click();
    await page.getByRole('cell', { name: t('ai_messages'), exact: true }).waitFor();
    await page.getByRole('link', { name: t('operations'), exact: true }).click();
    await page.getByRole('heading', { name: t('workerHealth'), exact: true }).waitFor();
  }
  assert.deepEqual(errors, []);
  console.log('SaaS browser smoke passed: Bulgarian/English registration, verification, trial, mock checkout, exact currency, usage and operations.');
} finally { await browser.close(); }
