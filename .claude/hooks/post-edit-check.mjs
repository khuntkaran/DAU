// PostToolUse (Write|Edit): formats and lints the edited file, then runs the
// tests that cover it, so a break is reported on the step that caused it.
import { existsSync } from 'node:fs';
import { basename, join } from 'node:path';
import { block, hasWebTool, isInsideRepo, readInput, root, sh, tail, toRepoPath, venvPython } from './lib/common.mjs';

const filePath = readInput().tool_input?.file_path;
if (!filePath) process.exit(0);

const repoPath = toRepoPath(filePath);
const skipped = !isInsideRepo(repoPath) || /(^|\/)(node_modules|\.next|\.venv|dist|coverage|alembic\/versions)\//.test(repoPath);
// The path reaches a shell, so anything that could break out of quotes is left alone.
if (skipped || /["$`%]/.test(repoPath)) process.exit(0);

const failures = [];
if (repoPath.endsWith('.py')) checkPython();
if (repoPath.startsWith('web/')) checkWeb();
if (failures.length > 0) block(failures.join('\n\n'));
remindAboutTests();

function checkPython() {
  const python = venvPython();
  if (!python) return;
  const quoted = `"${repoPath}"`;
  sh(`"${python}" -m ruff format ${quoted}`, 30_000);
  const lint = sh(`"${python}" -m ruff check --fix ${quoted}`, 30_000);
  if (!lint.ok) failures.push(`Ruff failed for ${repoPath}:\n${tail(lint.output)}`);

  const area = repoPath.split('/')[0];
  if (existsSync(join(root, area, 'tests'))) {
    const tests = sh(`"${python}" -m pytest ${area}/tests -q -x --no-header --no-cov`, 120_000);
    if (!tests.ok) failures.push(`Tests in ${area}/tests failed after editing ${repoPath}:\n${tail(tests.output)}`);
  }
}

function checkWeb() {
  const webRoot = join(root, 'web');
  const quoted = `"${repoPath.slice('web/'.length)}"`;
  if (/\.(tsx?|json|css|md)$/.test(repoPath) && hasWebTool('prettier')) {
    sh(`npx --no-install prettier --write --ignore-unknown ${quoted}`, 30_000, webRoot);
  }
  if (!/\.tsx?$/.test(repoPath)) return;
  if (hasWebTool('eslint')) {
    const lint = sh(`npx --no-install eslint --fix ${quoted}`, 60_000, webRoot);
    if (!lint.ok) failures.push(`ESLint failed for ${repoPath}:\n${tail(lint.output)}`);
  }
  if (hasWebTool('vitest')) {
    const tests = sh(`npx --no-install vitest related ${quoted} --run --passWithNoTests`, 120_000, webRoot);
    if (!tests.ok) failures.push(`Tests affected by ${repoPath} failed:\n${tail(tests.output)}`);
  }
}

/** Where the test for a source file should be, or null if it does not need one. */
function expectedTests(path) {
  const name = basename(path);
  const pythonSource = /^(rules|api\/app|worker)\/.+\.py$/.test(path);
  const pythonExempt = /(^|\/)tests\/|^__init__\.py$|^(main|models|schemas|conftest)\.py$/.test(path.includes('/tests/') ? path : name);
  if (pythonSource && !pythonExempt) {
    return [`${path.split('/')[0]}/tests/test_${name}`];
  }
  const webSource = /^web\/(components|lib)\/.+\.tsx?$/.test(path);
  if (webSource && !/\.(test|spec)\.|\.d\.ts$|\/index\.tsx?$/.test(path)) {
    const stem = path.replace(/\.tsx?$/, '');
    return [`${stem}.test.ts`, `${stem}.test.tsx`];
  }
  return null;
}

function remindAboutTests() {
  const expected = expectedTests(repoPath);
  if (!expected || expected.some((path) => existsSync(join(root, path)))) return;
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PostToolUse',
        additionalContext: `${repoPath} has no test file (expected ${expected[0]}). Add one in this step.`,
      },
    }),
  );
}
