# SuryaSetu delivery plan

The delivery manager keeps this file current. A task is `done` only when its check has passed on this machine.

Status values: `todo`, `doing`, `done`, `blocked`.

## Prerequisites from the team

| # | Item | Why | Status |
|---|---|---|---|
| P1 | Apply `.claude/settings.proposed.json` | Hooks and plugins are off until this is done | blocked |
| P2 | ~~Install Docker Desktop~~ | Not needed: local mode is SQLite and a local `uploads/` folder | dropped |
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
| Config, SQLite engine, enums (work plan 1.1, 1.2, 1.4) | Partner A | `npm run verify` | done |
| SQLAlchemy models for the 21 P0 tables (1.3) | Partner A | `api/tests/test_models.py` | done |
| Pydantic schemas and OpenAPI for all routes (1.4, 1.5) | Partner A | `api/tests/test_contract.py` | done |
| Rules return `steps[]` for the calculation panel (2.2) | Partner A | Golden tests | todo |
| Seed script with `--reset` (2.4) | Partner A | Fresh database from scratch | todo |

### Phase 3: Core flow, worth 30% of the score

| Task | Owner | Check | Status |
|---|---|---|---|
| OTP auth with roles (3.1) | Partner A | API tests | todo |
| Multipart uploads (3.2) | Partner A | API tests | todo |
| Requests with sizing and subsidy, map query (3.3, 3.4) | Partner A | API tests | todo |
| Quotes and transactional accept (3.5, 3.6) | Partner A | Double-accept race test | todo |
| Next.js setup, theme, i18n, API client | Frontend | Vitest and build | todo |
| Household flow: pin, photo, form, compare, accept | Frontend | Vitest | todo |
| Vendor flow: map and quote form | Frontend | Vitest | todo |
| Seed data: vendors, requests, planted quotes (2.5 to 2.9) | Partner B | Seed script loads it | todo |
| Request → quote → accept E2E | QA | Playwright | todo |

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
- 2026-11-01: The API contract is `api/app/schemas.py`, published as `api/openapi.json` (`npm run api:openapi`). A test fails if the file is stale. Unbuilt routes answer 501 in the standard error shape.
- 2026-11-01: The contract adds `GET /requests/mine`, `GET /quotes/mine` and `GET /requests/{id}/recommendation` to section 08, because the household and vendor screens need them.
- 2026-11-01: `Decimal` fields such as kW reach the web app as strings, so no precision is lost. Money stays `int` rupees.
- 2026-11-01: `GET /requests/{id}/quotes` is not paginated so all quotes can be compared side by side; the service caps a request at 50 quotes.
- 2026-11-01: The team's documents in `docs/previous/` now lead: SQLite locally with models that also run on PostgreSQL, the P0 tables and column names from `db-schema.html`, and the phases from `work-plan.html`. AI jobs run in `api/` with `BackgroundTasks`; uploads are multipart to `uploads/`. `rules/` stays at the root because it is already built and tested. This replaces the Docker, Redis and MinIO setup above for local work.
- 2026-11-01: The work plan says 22 P0 tables, but its list and `db-schema.html` name 21. All 21 are built.
- 2026-11-01: Statuses are lowercase, as in `db-schema.html`. Quote line items map to the rules checklist in `api/app/services/quotes.py`.
- 2026-11-01: Unbuilt routes answer 501 rather than the plan's mock JSON, so the frontend never shows invented numbers.
