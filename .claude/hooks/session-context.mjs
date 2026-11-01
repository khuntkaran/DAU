// SessionStart: tells Claude what state the checkout is in.
import { existsSync } from 'node:fs';
import { join } from 'node:path';
import { root, sh, venvPython } from './lib/common.mjs';

const lines = [];
const branch = sh('git branch --show-current', 10_000).output.trim();
if (branch) lines.push(`Git branch: ${branch}.`);

if (!existsSync(join(root, 'package.json'))) {
  lines.push('The project is not scaffolded yet. See docs/PLAN.md.');
} else {
  if (!venvPython()) lines.push('.venv is missing. Run: python -m venv .venv, then install requirements-dev.txt. Python checks are skipped until then.');
  if (!existsSync(join(root, '.env'))) lines.push('.env is missing. Ask the user to copy .env.example and add their keys.');
  if (!sh('docker --version', 10_000).ok) lines.push('Docker is not installed, so Postgres, Redis and MinIO cannot run here. API integration tests will not run.');
}
lines.push('Current status and next task: docs/PLAN.md.');

process.stdout.write(lines.join('\n'));
