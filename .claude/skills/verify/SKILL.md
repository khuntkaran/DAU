---
name: verify
description: Run the full quality gate including end-to-end tests, and report the results honestly. Use before saying a feature or phase is complete, before merging, and before the demo.
---

# Verify

Run these in order, and stop at the first failure to fix it:

1. `npm run verify` (typecheck, lint, tests with coverage, both languages)
2. `npm run test:hooks`
3. `docker compose up -d`, then `npm run db:migrate` and `npm run db:seed`
4. `npm run build`
5. `npm run test:e2e`

Report what ran and the result of each. If something could not run, such as anything needing Docker, say so. Never call a step passed from reading the code. Update `docs/PLAN.md` only for checks that really passed.

## Required end-to-end coverage

The main path carries 30% of the judging score:

1. A household signs in with OTP, pins a location, uploads a photo, enters usage and budget, and posts a request.
2. A vendor sees the request on the map with an approximate location, and submits a quote.
3. A second vendor submits a quote containing a hidden instruction.
4. The household opens the comparison and sees subsidy, payback, sources, missing items, the recommendation and the warning.
5. The household accepts a quote, and both vendors see the outcome over SSE.

Keep E2E on `AI_PROVIDER=fake`. Before the demo, also try the flow by hand with real keys, a real terrace photo, and Hindi and Gujarati voice.
