// Starts the API on :8000 and the UI on :3000. Usage: npm run dev
import { spawn } from 'node:child_process';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');

const servers = [
  { command: 'node scripts/py.mjs uvicorn api.app.main:app --reload --port 8000', cwd: root },
  { command: 'npm run dev', cwd: join(root, 'ui') },
].map(({ command, cwd }) => spawn(command, { cwd, shell: true, stdio: 'inherit' }));

function stopAll() {
  for (const server of servers) server.kill();
}

// If one server dies the app cannot work, so stop the other instead of half running.
for (const server of servers) {
  server.on('exit', (code) => {
    stopAll();
    process.exit(code ?? 0);
  });
}

process.on('SIGINT', stopAll);
process.on('SIGTERM', stopAll);
