# UI plan (Partner B, branch `ui`)

Source: `docs/previous/work-plan.html`, Partner B tasks, with types from `docs/previous/db-schema.html`.

Partner B owns the screens, the map, voice recording, the comparison view, sample data and the demo script.

Status: `todo`, `doing`, `done`. A task is `done` when its check has passed on this machine. The UI now runs on the real API, except for the gaps listed below.

## Folder layout

```
ui/src/
  routes/paths.ts       Main route file: every path, role home, navigation
  app/                  Next.js routes. Thin files that render a task's page
  tasks/<task>/
    api.ts              Endpoints for this task
    mock.ts             Mock of those endpoints, used until the backend exists
    types.ts            Types for this task
    ui/                 Screens and components for this task
  shared/               Client, session, i18n, common types, design system
```

The app calls the real API at `NEXT_PUBLIC_API_URL`. Unit tests set `NEXT_PUBLIC_API_MODE=mock`.

## Task list

| Work plan | Task | Folder | Status |
|---|---|---|---|
| 1.6 | All routes | `src/routes`, `src/app` | done |
| 1.7 | Leaflet map, loaded without SSR | `tasks/new-request/ui/MapPicker.tsx` | done |
| 1.8 | i18n in `en`, `hi`, `gu`, language switcher | `shared/i18n` | done |
| 1.9 | API client | `shared/api/client.ts` | done |
| 1.9 | Generate types from the real OpenAPI | `shared/api/schema.d.ts` | done |
| 2.5 | Seed: DISCOMs and tariff slabs | `seed/data/discoms.json` | todo |
| 2.6 | Seed: 20-30 vendors | `seed/data/vendors.json` | todo |
| 2.7 | Seed: 5 households, 6 requests | `seed/data/users.json`, `requests.json` | todo |
| 2.8 | Seed: about 15 quotes, including the 4 planted cases | `seed/data/quotes.json`, `components.json` | todo |
| 2.9 | Seed: 4-5 terrace photos | `seed/photos/` | todo, needs real photos |
| 3.7 | Login with OTP and demo buttons | `tasks/auth` | done |
| 3.8 | New request and estimate with sources | `tasks/new-request`, `tasks/rule-sources` | done |
| 3.9 | My requests and request detail | `tasks/my-requests` | done |
| 3.10 | Vendor map | `tasks/vendor-map` | done |
| 3.10 | Quote form with line items | `tasks/quote-form` | done |
| 3.11 | Compare and accept | `tasks/compare-quotes` | done |
| 4.6 | Obstruction boxes over the photo | `tasks/roof-assessment` | done |
| 4.7 | Voice in `hi`, `gu`, `en` | `tasks/voice-input` | done |
| 4.8 | Missing items, score breakdown, injection banner, recommendation | `tasks/compare-quotes`, `tasks/recommendation` | done |
| 4.9 | AI pending and failure states | `tasks/roof-assessment`, `tasks/recommendation` | done |
| Extra | Admin dashboard, request, vendor and review pages | `tasks/admin` | done |
| Extra | OTP expiry and attempt limit, demo buttons need the code | `tasks/auth` | done |
| Extra | Exact location: high accuracy, draggable pin, satellite, address search | `tasks/new-request` | done |
| Extra | Real speech input with number reading in three languages | `tasks/voice-input` | done |
| 5.4 | Savings calculator panel | Not started | todo, P1 |
| 5.5 | Tracker timeline | Not started | todo, P1 |
| 5.6 | Vendor profile page | Not started | todo, P1 |
| 6.3 | Demo script | `docs/` | todo |

`/admin` is in the route list, but the plan gives it no task, so it is a simple overview.

## Verified on 2026-11-01

- `npm run verify` in `ui/`: typecheck and lint clean, 152 tests pass. `npm run build` succeeds.
- `npm run test:e2e` in `ui/`: 113 of 113 browser checks pass in headless Chrome against the real API and a seeded database, with no console errors. The journey is the whole request → quote → accept path, plus location and voice. Admin checks run on sample data.

How each screen works and which file does what: [ui-guide.html](ui-guide.html). A test fails if that page goes out of date with `ui/src`.

## Not verified yet

- **Voice.** Headless Chrome cannot hear, so tests supply the transcript. Real speech needs a person to try it in Chrome or Edge. Gujarati and Hindi number words are read for common forms only.
- **GPS.** Tests supply the position. Accuracy depends on the device: phones are precise, and laptops without GPS only estimate.
- **AI features are not built on the backend.** Photo assessment, recommendation reasons and injection detection do not exist yet, so the UI says so rather than showing invented results.
- **Real phones and Safari.** Phone width was tested in desktop Chrome only.
- **Hindi and Gujarati wording** needs a native speaker's review. Text from the API, such as reasons and summaries, stays in English in the mock.

## API needed from Partner A

The UI expects these, in the shape of each task's `types.ts`:

| Method | Path | Used by |
|---|---|---|
| POST | `/auth/otp`, `/auth/verify` | `tasks/auth` |
| POST | `/uploads` (multipart) | `tasks/new-request` |
| POST | `/requests` | `tasks/new-request` |
| GET | `/requests/mine`, `/requests/{id}` | `tasks/my-requests` |
| GET | `/requests/{id}/assessment` | `tasks/roof-assessment` |
| GET | `/requests/open?bbox=` | `tasks/vendor-map` |
| GET | `/vendor/requests/{id}` | `tasks/quote-form` |
| POST | `/requests/{id}/quotes` | `tasks/quote-form` |
| GET | `/requests/{id}/quotes` | `tasks/compare-quotes` |
| POST | `/quotes/{id}/accept` | `tasks/compare-quotes` |
| POST, GET | `/requests/{id}/recommendation` | `tasks/recommendation` |
| GET | `/rules/current` | `tasks/rule-sources` |
| GET | `/admin/overview`, `/admin/requests`, `/admin/vendors`, `/admin/flagged-quotes` | `tasks/admin` |
| POST | `/admin/requests/{id}/cancel`, `/admin/vendors/{id}/{action}`, `/admin/flagged-quotes/{id}/review` | `tasks/admin` |

Voice uses the browser for now, so `/voice/transcribe` is not called. Its contract takes an uploaded audio key, and it can replace browser speech once Whisper works.

`/requests/{id}/assessment`, `/vendor/requests/{id}` and all `/admin` routes are not in the architecture's API table. The UI needs them, or the same data inside existing responses.

## Backend gaps found while connecting the UI

| Gap | Effect in the UI | Needed |
|---|---|---|
| `POST` and `GET /requests/{id}/recommendation` return 501 | Shows the top score with no reasons | The recommend job |
| `injection_detected` is always false | No warning banner on real quotes, though scoring still ignores notes | The injection guard, a bonus criterion |
| `roof_assessment` is always null | Shows the photo and "AI review is unavailable" | The photo job |
| `POST /voice/transcribe` returns 501 | The browser does the speech recognition | The voice job |
| No `/admin` routes | Admin pages show labelled sample data | The routes listed above |
| Vendor contact appears only in the accept response | The UI keeps it in local storage, so it is missing on another device | Add it to `GET /requests/{id}/quotes` |
| Request estimates have no cost or payback | Those two figures appear only on quotes | Optional: a benchmark cost |
| No seeded terrace photos | Seeded requests have no photo | Work plan task 2.9 |

## Points to agree with Partner A

1. **Worked example.** `work-plan.html` task 2.3 and the architecture say 3.8 years. Correct is ₹25,740 saved a year and 4.2 years, because saving is capped at consumption. `rules/tests/test_golden.py` already uses the correct value.
2. **Statuses.** The architecture uses uppercase with `INSTALLED`. The schema and work plan use lowercase with `completed`. The UI follows the schema.
3. **Score fields.** `rules/scoring.py` uses six criteria, while `quote_scores` has separate panel and inverter columns. The UI reads a `breakdown` map keyed by the `rules/` names.
4. **Database and uploads.** The work plan uses SQLite and multipart uploads. CLAUDE.md uses Postgres and presigned uploads. The UI follows the work plan, because it is the newest and the only one Docker is not needed for.
