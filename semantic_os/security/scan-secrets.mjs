import { execFileSync } from 'node:child_process';
import { readFileSync, readdirSync, lstatSync } from 'node:fs';
import { resolve, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

// Never print matches, file contents, environment values, or subprocess output.
export function secretValues(env) {
  const explicit = new Set((env.ONTELYX_SECRET_SCAN_KEYS || '').split(',').map(x => x.trim()).filter(Boolean));
  return Object.entries(env).filter(([key, value]) => value && (explicit.has(key) ||
    (!/^(VITE_|NEXT_PUBLIC_|PUBLIC_)/.test(key) && /(?:PASSWORD|SECRET|TOKEN|PRIVATE_KEY|DATABASE_URL|API_KEY|ACCESS_KEY)/i.test(key))))
    .flatMap(([key, value]) => {
      if (value.length < 8) return [];
      return [...new Set([value, encodeURIComponent(value), Buffer.from(value).toString('base64'), JSON.stringify(value).slice(1, -1)])]
        .map(value => ({ key, value }));
    });
}

export function detect(text, secrets) {
  return [...new Set(secrets.filter(item => text.includes(item.value)).map(item => item.key))];
}

function walk(path) {
  const stat = lstatSync(path);
  if (stat.isSymbolicLink()) throw new Error('Symlinks require explicit review');
  if (stat.isFile()) return [path];
  return readdirSync(path).flatMap(name => walk(resolve(path, name)));
}

function main() {
  const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
  const args = process.argv.slice(2);
  const files = new Set();
  if (!args.length) {
    const paths = execFileSync('git', ['ls-files', '-z', '--cached', '--others', '--exclude-standard'], { cwd: root, maxBuffer: 32 * 1024 * 1024 }).toString().split('\0').filter(Boolean);
    const deleted = new Set(execFileSync('git', ['ls-files', '-z', '--deleted'], { cwd: root }).toString().split('\0').filter(Boolean));
    paths.filter(path => !deleted.has(path)).forEach(path => files.add(resolve(root, path)));
  } else args.forEach(path => walk(resolve(path)).forEach(file => files.add(file)));
  const secrets = secretValues(process.env);
  let failed = false;
  for (const path of files) {
    const keys = detect(readFileSync(path).toString('utf8'), secrets);
    if (keys.length) {
      failed = true;
      console.error(`Secret exposure: ${JSON.stringify(relative(root, path))}; environment variable(s): ${keys.join(', ')}; values redacted.`);
    }
  }
  if (failed) process.exitCode = 1;
  else console.log(`Environment-secret scan passed: ${files.size} files. Pattern scanning is enforced separately by Gitleaks.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { main(); } catch { console.error('Secret scan could not complete; release blocked.'); process.exitCode = 2; }
}
