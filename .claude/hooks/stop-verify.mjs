// Stop: Claude may not finish a turn while typecheck, lint or tests fail.
// After MAX_BLOCKED_STOPS tries it hands over to the user instead of looping.
import { block, readCache, readInput, runGate, writeCache } from './lib/common.mjs';

const MAX_BLOCKED_STOPS = 3;

readInput();
const gate = runGate();
if (gate.ok) process.exit(0);

const cache = readCache();
const blockedStops = (cache.blockedStops ?? 0) + 1;

if (blockedStops > MAX_BLOCKED_STOPS) {
  writeCache({ ...cache, blockedStops: 0 });
  process.stdout.write(
    JSON.stringify({
      systemMessage: `Still failing after ${MAX_BLOCKED_STOPS} attempts: npm run ${gate.step}. Claude stopped so you can step in.`,
    }),
  );
  process.exit(0);
}

writeCache({ ...cache, blockedStops });
block(`Not done: \`npm run ${gate.step}\` failed (attempt ${blockedStops}/${MAX_BLOCKED_STOPS}). Fix it, or tell the user why you cannot.\n\n${gate.output}`);
