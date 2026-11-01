# SuryaSetu delivery plan

The delivery manager keeps this file current. A task is `done` only when its check has passed on this machine.

Status values: `todo`, `doing`, `done`, `blocked`.

## Prerequisites from the team

| # | Item | Why | Status |
|---|---|---|---|
| P1 | Apply `.claude/settings.proposed.json` | Hooks and plugins are off until this is done | blocked |
| P2 | Install Docker Desktop | Postgres with PostGIS, Redis and MinIO cannot run without it | blocked |
| P3 | Gemini and Groq free keys in `.env` | Real AI features and the final hand test | blocked |
| P4 | Confirm rule values marked `verify` in `rules/` | The brief requires public rules with sources | todo |

## Phases

### Phase 0: Foundations

| Task | Owner | Check | Status |
|---|---|---|---|
| Convert CLAUDE.md, skills and hooks to the design's stack | Manager | `npm run test:hooks` | done |
| Define the agent team | Manager | Agents listed by Claude Code | done |
| Root task runner, Python tooling, `.env.example` | Architect | `npm run verify` | done |

### Phase 1: Rules engine (no Docker needed)

| Task | Owner | Check | Status |
|---|---|---|---|
| Versioned YAML with citations | Architect | Loader tests | done |
| Sizing, subsidy, payback | Architect | Golden tests | done |
| Scoring and missing item checklist | Architect | Injection and ranking tests | done |

### Phase 2: Contract

Everyone works in parallel against this after it is agreed.

| Task | Owner | Check | Status |
|---|---|---|---|
| `docker-compose.yml` for all six services | Architect | `docker compose up` healthy | blocked by P2 |
| SQLAlchemy models and first migration | Backend | `npm run db:migrate` | blocked by P2 |
| Pydantic schemas and OpenAPI for all routes | Backend | Schema test | doing |

### Phase 3: Core flow, worth 30% of the score

| Task | Owner | Check | Status |
|---|---|---|---|
| OTP auth with roles | Backend | API tests | blocked by P2 |
| Requests with sizing and subsidy, map query | Backend | API tests | blocked by P2 |
| Quotes and transactional accept | Backend | Double-accept race test | blocked by P2 |
| Presigned uploads | Backend | API tests | blocked by P2 |
| Next.js setup, theme, i18n, API client | Frontend | Vitest and build | todo |
| Household flow: pin, photo, form, compare, accept | Frontend | Vitest | todo |
| Vendor flow: map and quote form | Frontend | Vitest | todo |
| Seed: 30 vendors, 3 requests, 1 injection quote | Backend | `npm run db:seed` | blocked by P2 |
| Request → quote → accept E2E | QA | Playwright | blocked by P2 |

### Phase 4: AI

| Task | Owner | Check | Status |
|---|---|---|---|
| LLM gateway, token bucket, cache, fallback, fake provider | AI | Worker tests | todo |
| Injection guard | AI | Worker tests | todo |
| Photo assessment job | AI | Worker tests | todo |
| Voice job in `en`, `hi`, `gu` | AI | Worker tests | todo |
| Quote review and recommendation jobs | AI | Worker tests | todo |
| SSE notifications | Backend | API tests | blocked by P2 |
| Photo boxes, recommendation, citations, voice UI | Frontend | Vitest | todo |

### Phase 5: Finish

| Task | Owner | Check | Status |
|---|---|---|---|
| Full review of each module | QA | Review findings closed | todo |
| `docs/ARCHITECTURE.md` with corrected example | Architect | Matches the built code | todo |
| Hand test with real keys, Hindi and Gujarati voice | Team | Done by a person | blocked by P3 |
| Presentation rehearsal | Team | Done by people | todo |

## Decisions

- 2026-11-01: The architecture HTML sets the stack. It replaces the earlier React, Node and Material UI plan, so Tailwind is used rather than MUI.
- 2026-11-01: Code targets Python 3.11+, because this machine has 3.11 and containers use 3.12.
- 2026-11-01: `npm run` is the single entry point, because `make` is not installed here.
- 2026-11-01: `GENERATION` stays at the design's 120 kWh but is shown as an assumption, because no MNRE source was found.
- 2026-11-01: The design's worked example is wrong. The correct saving is ₹25,740 and payback is 4.2 years.
- 2026-11-01: Agents share one working tree instead of worktrees, because their paths do not overlap and `origin` has no branches for a worktree to start from.
- 2026-11-01: Until P1 is done, hooks do not run, so the manager runs `npm run verify` after every agent task.
