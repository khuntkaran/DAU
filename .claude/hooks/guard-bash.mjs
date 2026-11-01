// PreToolUse (Bash|PowerShell): stops commands that bypass the project's
// safety checks, and runs the full gate before anything is committed or pushed.
import { block, readInput, runGate } from './lib/common.mjs';

const command = readInput().tool_input?.command ?? '';

const FORBIDDEN = [
  [/--no-verify\b/, 'Do not bypass git hooks. Fix what the hook reports.'],
  [/\bgit\s+push\b.*(--force\b|--force-with-lease\b|\s-f\b)/, 'Force pushes rewrite teammates\' work. Ask the user to do this themselves.'],
  [/\bgit\s+reset\s+--hard\b/, 'git reset --hard discards work. Ask the user first.'],
  [/\bdocker[\s-]compose\s+down\b.*(\s-v\b|--volumes\b)/, 'This deletes the database and photo volumes. Ask the user first.'],
  [/\bdocker\s+(system|volume)\s+(prune|rm)\b/, 'This deletes Docker data. Ask the user first.'],
];

for (const [pattern, reason] of FORBIDDEN) {
  if (pattern.test(command)) block(reason);
}

if (/\bgit\s+(commit|push)\b/.test(command)) {
  const gate = runGate();
  if (!gate.ok) block(`Blocked: \`npm run ${gate.step}\` failed. Fix it before committing.\n\n${gate.output}`);
}
