// Runs a Python module from the project's virtualenv on any OS.
// Usage: node scripts/py.mjs pytest rules/tests
import { spawnSync } from 'node:child_process';
import { existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
// The .venv committed to Git was built on another machine, so a local one outside the repo wins.
const python = [
  join(root, '..', '.venv-api', 'Scripts', 'python.exe'),
  join(root, '.venv', 'Scripts', 'python.exe'),
  join(root, '.venv', 'bin', 'python'),
].find(existsSync);

if (!python) {
  console.error('.venv not found. Run: python -m venv .venv');
  process.exit(1);
}

const result = spawnSync(python, ['-m', ...process.argv.slice(2)], { cwd: root, stdio: 'inherit' });
process.exit(result.status ?? 1);
