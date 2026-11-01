// PreToolUse (Write|Edit): refuses edits that would leak secrets, weaken tests
// or rewrite history that teammates have already applied.
import { block, isInsideRepo, readInput, sh, toRepoPath } from './lib/common.mjs';

const input = readInput();
const filePath = input.tool_input?.file_path;
if (!filePath) process.exit(0);

const repoPath = toRepoPath(filePath);
const content = [input.tool_input.content, input.tool_input.new_string].filter(Boolean).join('\n');

const isEnvFile = /(^|\/)\.env(\.|$)/.test(repoPath) && !/(^|\/)\.env\.example$/.test(repoPath);
if (isEnvFile) block(`${repoPath} holds secrets. Add the variable name to .env.example and ask the user to set the value.`);

if (/\.(pem|key|p12)$/.test(repoPath)) block(`${repoPath} looks like a private key and must not be written by Claude.`);

const SECRET = /AIza[0-9A-Za-z_-]{35}|gsk_[A-Za-z0-9]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----/;
if (!repoPath.startsWith('.claude/') && SECRET.test(content)) {
  block('This edit contains what looks like a live API key or private key. Read it from the environment instead.');
}

const SKIP_MESSAGE = 'Do not skip or focus tests. Fix the code, or fix the test if its expectation is wrong.';
const isTsTest = /\.(test|spec)\.tsx?$/.test(repoPath);
if (isTsTest && /\b(it|test|describe)\.(skip|only|todo)\s*\(/.test(content)) block(SKIP_MESSAGE);

const isPyTest = /(^|\/)(test_[^/]+|conftest)\.py$/.test(repoPath);
if (isPyTest && /pytest\.mark\.(skip|skipif|xfail)|pytest\.(skip|xfail)\s*\(|unittest\.skip/.test(content)) block(SKIP_MESSAGE);

// Applied migrations are immutable; schema changes go in a new revision.
if (isInsideRepo(repoPath) && /(^|\/)alembic\/versions\/.+\.py$/.test(repoPath)) {
  if (sh(`git ls-files --error-unmatch "${repoPath}"`, 10_000).ok) {
    block(`${repoPath} is a committed migration. Create a new revision with: npm run db:revision`);
  }
}
