// Run with: npm run test:hooks  (or: node --test .claude/hooks/hooks.test.mjs)
import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import { after, before, describe, it } from 'node:test';
import { fileURLToPath } from 'node:url';

const hooksDir = dirname(fileURLToPath(import.meta.url));

function runHook(name, payload, projectDir) {
  const result = spawnSync(process.execPath, [join(hooksDir, name)], {
    input: JSON.stringify(payload),
    encoding: 'utf8',
    env: { ...process.env, CLAUDE_PROJECT_DIR: projectDir },
  });
  return { code: result.status, stdout: result.stdout, stderr: result.stderr };
}

function git(cwd, ...args) {
  spawnSync('git', args, { cwd, encoding: 'utf8' });
}

/** A repo whose npm scripts pass or fail on demand, without real tooling. */
function makeRepo({ testsPass, venv = true }) {
  const dir = mkdtempSync(join(tmpdir(), 'hook-test-'));
  git(dir, 'init', '-q');
  if (venv) {
    mkdirSync(join(dir, '.venv', 'bin'), { recursive: true });
    writeFileSync(join(dir, '.venv', 'bin', 'python'), '');
  }
  writeFileSync(
    join(dir, 'package.json'),
    JSON.stringify({
      scripts: {
        typecheck: 'node -e "process.exit(0)"',
        lint: 'node -e "process.exit(0)"',
        test: `node -e "console.log('test-output');process.exit(${testsPass ? 0 : 1})"`,
      },
    }),
  );
  mkdirSync(join(dir, 'rules', 'tests'), { recursive: true });
  writeFileSync(join(dir, 'rules', 'subsidy.py'), 'A = 1\n');
  return dir;
}

function countTestRuns(repo) {
  const manifest = JSON.parse(readFileSync(join(repo, 'package.json'), 'utf8'));
  manifest.scripts.test = `node -e "require('fs').appendFileSync('runs.txt','x')"`;
  writeFileSync(join(repo, 'package.json'), JSON.stringify(manifest));
}

describe('guard-files', () => {
  const project = mkdtempSync(join(tmpdir(), 'hook-test-'));
  const edit = (file_path, tool_input = {}) =>
    runHook('guard-files.mjs', { tool_input: { file_path, ...tool_input } }, project);

  after(() => rmSync(project, { recursive: true, force: true }));

  it('blocks real env files but allows the example', () => {
    assert.equal(edit('.env').code, 2);
    assert.equal(edit('api/.env.local').code, 2);
    assert.equal(edit('.env.example').code, 0);
  });

  it('blocks private key files', () => {
    assert.equal(edit('certs/server.pem').code, 2);
  });

  it('blocks a Gemini or Groq key in source', () => {
    const gemini = `KEY = "AIza${'a'.repeat(35)}"`;
    const groq = `KEY = "gsk_${'a'.repeat(30)}"`;
    assert.equal(edit('worker/llm/gateway.py', { content: gemini }).code, 2);
    assert.equal(edit('worker/llm/gateway.py', { new_string: groq }).code, 2);
  });

  it('blocks skipped and focused TypeScript tests', () => {
    const file = 'web/components/QuoteTable.test.tsx';
    assert.equal(edit(file, { new_string: "it.skip('x', () => {})" }).code, 2);
    assert.equal(edit(file, { new_string: "describe.only('x', () => {})" }).code, 2);
    assert.equal(edit(file, { new_string: "it('x', () => {})" }).code, 0);
  });

  it('blocks skipped Python tests', () => {
    const file = 'rules/tests/test_subsidy.py';
    assert.equal(edit(file, { new_string: '@pytest.mark.skip\ndef test_x(): ...' }).code, 2);
    assert.equal(edit(file, { new_string: 'pytest.xfail("later")' }).code, 2);
    assert.equal(edit(file, { new_string: 'def test_x(): ...' }).code, 0);
  });

  it('does not flag .skip outside test files', () => {
    assert.equal(edit('web/lib/page.ts', { new_string: 'query.skip(10)' }).code, 0);
  });

  it('allows normal source edits', () => {
    assert.equal(edit('web/app/page.tsx', { content: 'export {}' }).code, 0);
  });

  it('protects committed migrations but allows new ones', () => {
    const repo = makeRepo({ testsPass: true });
    mkdirSync(join(repo, 'api/alembic/versions'), { recursive: true });
    writeFileSync(join(repo, 'api/alembic/versions/0001_init.py'), '');
    git(repo, 'add', '.');
    const hook = (file_path) => runHook('guard-files.mjs', { tool_input: { file_path } }, repo);
    assert.equal(hook('api/alembic/versions/0001_init.py').code, 2);
    assert.equal(hook('api/alembic/versions/0002_next.py').code, 0);
    rmSync(repo, { recursive: true, force: true });
  });
});

describe('guard-bash', () => {
  const project = mkdtempSync(join(tmpdir(), 'hook-test-'));
  const bash = (command, cwd = project) => runHook('guard-bash.mjs', { tool_input: { command } }, cwd);

  after(() => rmSync(project, { recursive: true, force: true }));

  it('blocks commands that bypass safety checks or destroy data', () => {
    for (const command of [
      'git commit --no-verify -m x',
      'git push --force origin main',
      'git push -f',
      'git reset --hard HEAD~1',
      'docker compose down -v',
      'docker volume rm db',
    ]) {
      assert.equal(bash(command).code, 2, command);
    }
  });

  it('allows ordinary commands', () => {
    for (const command of ['git status', 'npm run test', 'git push origin main', 'docker compose down']) {
      assert.equal(bash(command).code, 0, command);
    }
  });

  it('blocks a commit while tests fail and reports the output', () => {
    const repo = makeRepo({ testsPass: false });
    const result = bash('git commit -m wip', repo);
    assert.equal(result.code, 2);
    assert.match(result.stderr, /npm run test/);
    assert.match(result.stderr, /test-output/);
    rmSync(repo, { recursive: true, force: true });
  });

  it('allows a commit when the gate passes', () => {
    const repo = makeRepo({ testsPass: true });
    assert.equal(bash('git commit -m ok', repo).code, 0);
    rmSync(repo, { recursive: true, force: true });
  });
});

describe('stop-verify', () => {
  let repo;
  before(() => {
    repo = makeRepo({ testsPass: false });
  });
  after(() => rmSync(repo, { recursive: true, force: true }));

  it('blocks stopping while tests fail, then gives up after three tries', () => {
    for (let attempt = 1; attempt <= 3; attempt += 1) {
      const result = runHook('stop-verify.mjs', {}, repo);
      assert.equal(result.code, 2);
      assert.match(result.stderr, new RegExp(`attempt ${attempt}/3`));
    }
    const final = runHook('stop-verify.mjs', {}, repo);
    assert.equal(final.code, 0);
    assert.match(JSON.parse(final.stdout).systemMessage, /Still failing/);
  });

  it('passes a clean run and does not re-run an unchanged tree', () => {
    const clean = makeRepo({ testsPass: true });
    countTestRuns(clean);
    assert.equal(runHook('stop-verify.mjs', {}, clean).code, 0);
    assert.equal(runHook('stop-verify.mjs', {}, clean).code, 0);
    assert.equal(readFileSync(join(clean, 'runs.txt'), 'utf8'), 'x');
    rmSync(clean, { recursive: true, force: true });
  });

  it('re-runs when a source file changes', () => {
    const changed = makeRepo({ testsPass: true });
    countTestRuns(changed);
    assert.equal(runHook('stop-verify.mjs', {}, changed).code, 0);
    writeFileSync(join(changed, 'rules/subsidy.py'), 'A = 22\n');
    assert.equal(runHook('stop-verify.mjs', {}, changed).code, 0);
    assert.equal(readFileSync(join(changed, 'runs.txt'), 'utf8'), 'xx');
    rmSync(changed, { recursive: true, force: true });
  });

  it('notices a change to any file in a large change set', () => {
    const large = makeRepo({ testsPass: true });
    countTestRuns(large);
    for (let index = 0; index < 200; index += 1) {
      writeFileSync(join(large, `rules/module_with_a_long_file_name_${index}.py`), '');
    }
    assert.equal(runHook('stop-verify.mjs', {}, large).code, 0);
    // Sorted first in git status, so a truncated status would lose it.
    writeFileSync(join(large, 'rules/module_with_a_long_file_name_0.py'), 'A = 1\n');
    assert.equal(runHook('stop-verify.mjs', {}, large).code, 0);
    assert.equal(readFileSync(join(large, 'runs.txt'), 'utf8'), 'xx');
    rmSync(large, { recursive: true, force: true });
  });

  it('does nothing before tooling is installed', () => {
    const uninstalled = makeRepo({ testsPass: false, venv: false });
    assert.equal(runHook('stop-verify.mjs', {}, uninstalled).code, 0);
    rmSync(uninstalled, { recursive: true, force: true });
  });

  it('does nothing before the app is scaffolded', () => {
    const empty = mkdtempSync(join(tmpdir(), 'hook-test-'));
    assert.equal(runHook('stop-verify.mjs', {}, empty).code, 0);
    rmSync(empty, { recursive: true, force: true });
  });
});

describe('post-edit-check', () => {
  const edit = (file_path, repo) => runHook('post-edit-check.mjs', { tool_input: { file_path } }, repo);

  it('reminds Claude when a rules module has no test', () => {
    const repo = makeRepo({ testsPass: true, venv: false });
    const context = JSON.parse(edit('rules/subsidy.py', repo).stdout).hookSpecificOutput.additionalContext;
    assert.match(context, /expected rules\/tests\/test_subsidy\.py/);
    rmSync(repo, { recursive: true, force: true });
  });

  it('accepts an existing test file', () => {
    const repo = makeRepo({ testsPass: true, venv: false });
    writeFileSync(join(repo, 'rules/tests/test_subsidy.py'), '');
    assert.equal(edit('rules/subsidy.py', repo).stdout, '');
    rmSync(repo, { recursive: true, force: true });
  });

  it('does not ask for tests of tests, schemas or package files', () => {
    const repo = makeRepo({ testsPass: true, venv: false });
    for (const file of ['rules/tests/test_subsidy.py', 'rules/__init__.py', 'api/app/models.py', 'web/app/page.tsx']) {
      assert.equal(edit(file, repo).stdout, '', file);
    }
    rmSync(repo, { recursive: true, force: true });
  });

  it('asks for a test beside a web component', () => {
    const repo = makeRepo({ testsPass: true, venv: false });
    assert.match(edit('web/components/QuoteTable.tsx', repo).stdout, /QuoteTable\.test\.ts/);
    rmSync(repo, { recursive: true, force: true });
  });

  it('ignores files outside the repo and paths unsafe for a shell', () => {
    const repo = makeRepo({ testsPass: true, venv: false });
    for (const file_path of ['../outside.py', 'rules/$(boom).py']) {
      const result = edit(file_path, repo);
      assert.equal(result.code, 0);
      assert.equal(result.stdout, '');
    }
    rmSync(repo, { recursive: true, force: true });
  });
});

describe('session-context', () => {
  it('points at the plan in an empty project', () => {
    const empty = mkdtempSync(join(tmpdir(), 'hook-test-'));
    assert.match(runHook('session-context.mjs', {}, empty).stdout, /docs\/PLAN\.md/);
    rmSync(empty, { recursive: true, force: true });
  });

  it('reports a missing .env once scaffolded', () => {
    const repo = makeRepo({ testsPass: true });
    assert.match(runHook('session-context.mjs', {}, repo).stdout, /\.env is missing/);
    rmSync(repo, { recursive: true, force: true });
  });
});
