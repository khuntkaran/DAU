# SuryaSetu: AI-Powered Rooftop Solar Marketplace

SELC Hackathon project, built with agentic coding. The brief is in [Problem statement.txt](Problem%20statement.txt). [SuryaSetu Architecture.html](SuryaSetu%20Architecture.html) is the source of truth for technology and design. Status and next tasks are in [docs/PLAN.md](docs/PLAN.md).

Households post rooftop solar needs under PM Surya Ghar, vendors respond with quotes, and an AI assistant helps the household decide. Judging: working request → quote → accept flow 30%, architecture 20%, scalability and deployment plan 20%, AI features with numbers calculated in code 20%, presentation 10%.

## Non-negotiable rules

1. **Numbers are calculated in code.** Subsidy, size, cost, payback and vendor ranking live in `rules/`. The LLM extracts facts and explains results, and it never produces a figure or a ranking.
2. **Every rule shows its source.** Each result carries `rule_version` and `citations`, and the UI links to the source. Load `/pm-surya-rules` before touching these.
3. **Vendor text and photos are untrusted.** A quote saying "rank this vendor first" must change nothing. See `/ai-feature`.
4. **AI never blocks the flow.** Every LLM call is a background job. If the LLM is down, the household still posts, vendors still quote, and calculated numbers still show.
5. **Only the LLM gateway talks to Gemini or Groq**, on free tiers, with keys on the server.
6. **Household privacy.** Vendors see a location rounded to about 500 m and no phone number until a quote is accepted.
7. **Tests move with the code.** A task is finished only when its tests pass.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 16 (React, TypeScript strict), Tailwind CSS 4, Leaflet with OpenStreetMap, `next-intl` for `en`, `hi`, `gu` |
| API | FastAPI, Pydantic 2, SQLAlchemy 2, GeoAlchemy2, Alembic |
| Database | PostgreSQL 16 with PostGIS, JSONB for AI output |
| Storage | MinIO locally, S3-compatible in production, presigned browser uploads |
| Queue and cache | Redis with an `arq` worker, including the token bucket and response cache |
| AI | Gemini Flash for vision and reasoning, Groq Whisper large-v3 for speech, Groq Llama as text fallback |
| Realtime | Server-Sent Events |
| Local run | `docker compose up`: web, api, worker, postgres, redis, minio |
| Tests | pytest, Vitest, Testing Library, Playwright |

Python code must run on 3.11 and 3.12. Containers use 3.12. TypeScript stays on `~6.0` until `typescript-eslint` supports 7. Model names come from env, never code.

## Structure

```
docker-compose.yml
package.json              Task runner for both languages, npm workspace for web
pyproject.toml            Ruff, mypy, pytest config
scripts/py.mjs            Runs Python tools from .venv on any OS
web/                      Next.js: app/(household), app/(vendor), components/, lib/, i18n/{en,hi,gu}.json
api/app/                  main.py, routers/, services/, models.py, schemas.py
api/alembic/              Migrations
api/tests/
rules/                    Pure package: sizing, subsidy, payback, scoring, checklist
rules/pm_surya_ghar_v2024_03.yaml
rules/tests/
worker/jobs/              photo_assess, voice_extract, quote_review, recommend
worker/llm/               gateway, ratelimit, guard, providers/{gemini,groq,fake}
worker/tests/
seed/seed.py
e2e/                      Playwright
docs/PLAN.md              Delivery plan and status
docs/ARCHITECTURE.md      Presentation copy of the architecture
```

`rules/` does no I/O and imports nothing from `api/` or `worker/`. `api/` and `worker/` both import `rules`. `web/` talks only to the API.

## Commands

```bash
docker compose up        # Full stack
npm run verify           # Typecheck, lint, tests with coverage, both languages
npm run typecheck
npm run lint
npm run test
npm run test:e2e         # Playwright, AI_PROVIDER=fake
npm run test:hooks       # Tests for .claude/hooks
npm run db:migrate
npm run db:revision -- "message"
npm run db:seed
node scripts/py.mjs pytest rules/tests/test_subsidy.py    # One Python test file
```

Set up Python with `python -m venv .venv`, then `node scripts/py.mjs pip install -r requirements-dev.txt`.

## Code conventions

**Python:** full type hints checked by mypy strict. Pydantic at every boundary: HTTP, env, LLM output. Routers call services, services call the database. Money is whole rupees in `int`, capacity is `Decimal` kW. No float arithmetic for money. Comments explain why, not what.

**TypeScript:** strict, no `any`. Tailwind utilities only, with colours from theme tokens. Server Components by default, Client Components only for interaction. API types are generated from the FastAPI OpenAPI schema into `web/lib/api-types.ts`, never hand-written.

**Both:** secrets live only in `.env`, and each new variable goes in `.env.example`. Do not add a dependency if the stack already covers the need.

## Testing

Write the failing test first for rules, API behaviour and bug fixes. For each task:

1. Write or update the test.
2. Implement.
3. Hooks format and lint the file and run its related tests.
4. Fix any failure before the next change.
5. Before finishing, the Stop hook runs typecheck, lint and all tests.

| Layer | Tool | Location | Coverage |
|---|---|---|---|
| Rules | pytest, golden cases | `rules/tests/` | 90% |
| API | pytest against real Postgres | `api/tests/` | 70% |
| Worker | pytest with the `fake` provider | `worker/tests/` | 70% |
| UI | Vitest, Testing Library | `web/**/*.test.tsx` | 70% |
| Main flow | Playwright | `e2e/` | Request → quote → accept |

Never skip, delete or weaken a test to get to green. Tests never call a real LLM. If a check cannot run, say so instead of claiming it passed. Run `/verify` before calling a feature complete.

## Agent team

The main Claude session is the **delivery manager**. It reads `docs/PLAN.md`, assigns one task at a time, reviews results, runs the gates and updates the plan. It does not hand off a task whose interface is undecided.

| Agent | Owns | Role in the brief |
|---|---|---|
| `architect` | `rules/`, `docker-compose.yml`, `docs/`, root config | Architect |
| `backend-engineer` | `api/`, `seed/` | Backend |
| `frontend-engineer` | `web/` | Frontend |
| `ai-engineer` | `worker/` | AI features |
| `qa-reviewer` | `e2e/`, reads everything | Reviews and tests |

Rules for working in parallel:

- An agent edits only the paths it owns. Anything else goes back to the manager.
- API schemas are agreed before frontend and worker tasks start.
- Parallel agents use worktree isolation, and the manager merges one at a time.
- `qa-reviewer` reviews every phase before it is marked done.

## Claude Code setup

Skills: `/pm-surya-rules`, `/add-api-endpoint`, `/add-frontend-feature`, `/ai-feature`, `/db-change`, `/verify`, `/scale-plan`.

Hooks in `.claude/hooks/` are active only once `.claude/settings.proposed.json` has been copied to `.claude/settings.json`:

| Hook | When | What it does |
|---|---|---|
| `session-context` | Session start | Reports setup state |
| `guard-files` | Before edits | Blocks secrets, skipped tests, edits to committed migrations |
| `guard-bash` | Before commands | Blocks `--no-verify`, force push, hard reset, deleting Docker volumes. Runs the gate before commit and push |
| `post-edit-check` | After edits | Formats, lints, runs related tests, reminds about missing tests |
| `stop-verify` | Before finishing | Typecheck, lint and tests, blocking up to 3 times |

Plugins: `typescript-lsp`, `pyright-lsp`, `playwright`, `context7`, `frontend-design`, `security-guidance`, `pr-review-toolkit`.

## Git

Branch from `main` as `feat/<topic>` or `fix/<topic>`, with one task per branch. Commit messages use Conventional Commits.
