import { test } from 'node:test';
import assert from 'node:assert/strict';
import { secretValues, detect } from './scan-secrets.mjs';
import { spawnSync } from 'node:child_process';

test('detects raw, URI encoded, base64 and JSON escaped private values', () => {
  const value = ['synthetic', 'credential', '/line\nvalue'].join('-');
  const secrets = secretValues({ DATABASE_URL: value });
  for (const encoded of [value, encodeURIComponent(value), Buffer.from(value).toString('base64'), JSON.stringify(value).slice(1, -1)]) {
    assert.deepEqual(detect(`bundle: ${encoded}`, secrets), ['DATABASE_URL']);
  }
  assert.deepEqual(detect('no credential here', secrets), []);
});

test('public configuration is excluded unless explicitly marked secret', () => {
  const value = 'synthetic-public-value';
  assert.equal(secretValues({ VITE_API_KEY: value }).length, 0);
  assert.deepEqual(detect(value, secretValues({ VITE_API_KEY: value, ONTELYX_SECRET_SCAN_KEYS: 'VITE_API_KEY' })), ['VITE_API_KEY']);
});

test('CLI blocks detected values without echoing them', () => {
  const value = 'synthetic-public-value';
  const result = spawnSync(process.execPath, ['semantic_os/security/scan-secrets.mjs', 'semantic_os/security/scan-secrets.test.mjs'], {
    cwd: new URL('../..', import.meta.url), encoding: 'utf8',
    env: { ...process.env, ONTELYX_SCAN_TEST_SECRET: value },
  });
  assert.equal(result.status, 1);
  assert.ok(result.stderr.includes('ONTELYX_SCAN_TEST_SECRET'));
  assert.ok(!result.stderr.includes(value));
});

test('CLI blocks missing artifact directories', () => {
  const result = spawnSync(process.execPath, ['semantic_os/security/scan-secrets.mjs', 'missing-artifact-for-secret-scan-test'], {
    cwd: new URL('../..', import.meta.url), encoding: 'utf8',
  });
  assert.equal(result.status, 2);
});
