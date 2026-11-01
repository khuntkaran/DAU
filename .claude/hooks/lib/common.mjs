// Shared helpers for the Claude Code hooks in this folder.
// Hooks are plain Node with no dependencies so they run before anything is installed.
import { spawnSync } from 'node:child_process';
import { createHash } from 'node:crypto';
import { existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve } from 'node:path';

export const root = resolve(process.env.CLAUDE_PROJECT_DIR || process.cwd());
const cacheFile = join(root, '.claude', '.cache', 'verify.json');
const OUTPUT_TAIL_CHARS = 3000;
const GATE_STEP_TIMEOUT_MS = 240_000;

/** Files whose change means the gate has to run again. */
const GATED_PATH = /^(ui|api|rules|worker|seed)\/|^(package\.json|package-lock\.json|pyproject\.toml|requirements[^/]*\.txt)$/;

export function readInput() {
  try {
    return JSON.parse(readFileSync(0, 'utf8') || '{}');
  } catch {
    return {};
  }
}

export function toRepoPath(filePath) {
  return relative(root, resolve(root, filePath)).replaceAll('\\', '/');
}

export function isInsideRepo(repoPath) {
  return !repoPath.startsWith('../') && !repoPath.startsWith('/') && !/^[A-Za-z]:/.test(repoPath);
}

/** Runs through a shell because npm and npx are .cmd shims on Windows. */
export function sh(command, timeout = GATE_STEP_TIMEOUT_MS, cwd = root) {
  const result = spawnSync(command, { cwd, shell: true, encoding: 'utf8', timeout });
  return { ok: result.status === 0, output: `${result.stdout ?? ''}${result.stderr ?? ''}` };
}

/** Keeps a failure report short enough to feed back to Claude. */
export function tail(output) {
  return output.slice(-OUTPUT_TAIL_CHARS);
}

/** Path of the project's virtualenv Python, or null before it is created. */
export function venvPython() {
  const candidates = [join('.venv', 'Scripts', 'python.exe'), join('.venv', 'bin', 'python')];
  return candidates.find((path) => existsSync(join(root, path))) ?? null;
}

/** True when a Node tool from ui/ is installed. */
export function hasUiTool(name) {
  return ['node_modules', join('ui', 'node_modules')].some((dir) => existsSync(join(root, dir, '.bin', name)));
}

export function npmScripts() {
  const manifest = join(root, 'package.json');
  if (!existsSync(manifest)) return {};
  try {
    return JSON.parse(readFileSync(manifest, 'utf8')).scripts ?? {};
  } catch {
    return {};
  }
}

export function readCache() {
  try {
    return JSON.parse(readFileSync(cacheFile, 'utf8'));
  } catch {
    return {};
  }
}

export function writeCache(value) {
  mkdirSync(dirname(cacheFile), { recursive: true });
  writeFileSync(cacheFile, JSON.stringify(value, null, 2));
}

/** Hash of gated working-tree changes; null when there are none. */
export function fingerprint() {
  const status = sh('git status --porcelain -uall', 30_000);
  if (!status.ok) return null;
  const entries = status.output
    .split('\n')
    .map((line) => line.slice(3).trim().replaceAll('"', ''))
    .filter((path) => GATED_PATH.test(path))
    .sort();
  if (entries.length === 0) return null;
  const hash = createHash('sha256');
  for (const path of entries) {
    const full = join(root, path);
    hash.update(path);
    if (existsSync(full)) {
      const { size, mtimeMs } = statSync(full);
      hash.update(`${size}:${mtimeMs}`);
    }
  }
  return hash.digest('hex');
}

/**
 * Runs typecheck, lint and tests, skipping scripts that do not exist yet.
 * A tree that already passed is not re-run.
 */
export function runGate() {
  const scripts = npmScripts();
  const steps = ['typecheck', 'lint', 'test'].filter((step) => scripts[step]);
  const installed = venvPython() !== null || hasUiTool('next');
  if (steps.length === 0 || !installed) return { ok: true, skipped: true };

  const print = fingerprint();
  if (print === null) return { ok: true, skipped: true };

  const cache = readCache();
  if (cache.passed === print) return { ok: true, skipped: true };

  for (const step of steps) {
    const result = sh(`npm run --silent ${step}`);
    if (!result.ok) return { ok: false, step, output: tail(result.output) };
  }
  writeCache({ passed: print, blockedStops: 0 });
  return { ok: true, skipped: false };
}

export function block(message) {
  process.stderr.write(`${message}\n`);
  process.exit(2);
}
