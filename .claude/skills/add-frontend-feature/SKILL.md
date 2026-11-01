---
name: add-frontend-feature
description: Build a household or vendor screen or component in ui/ with Next.js, Tailwind and tests. Use for any React, Tailwind, Leaflet map, photo upload, quote comparison, voice UI or translation work.
argument-hint: "[feature or screen]"
---

# Add a frontend feature

Target: $ARGUMENTS

## Structure

```
ui/src/routes/paths.ts    Every path. Links and redirects come from here
ui/src/app/               Next.js routes, thin files that render a task's page
ui/src/tasks/<task>/
  api.ts                  Endpoints. Picks the real client or the mock
  mock.ts                 Mock of those endpoints until the backend exists
  types.ts                Types for this task
  ui/                     Screens and components, each with a .test.tsx
ui/src/shared/            Client, session, i18n, design system, mock store
```

The task list and API contract are in `docs/UI-PLAN.md`. Add a route to `paths.ts` first, then a thin page in `app/`.

## Rules

- **Tailwind only**, with colours from the theme tokens in `ui/src/app/globals.css`. No other UI kit and no hard-coded hex values in components.
- **Server Components by default.** Add `"use client"` only for interaction, the map, recording or SSE.
- **Types live with the task.** Replace them with generated types when the real OpenAPI exists.
- **Every data screen handles** loading, error with retry, empty and success.
- **No business maths in the browser.** Subsidy, payback and scores come from the API, with an ⓘ source link from `<RuleSource />`.
- **Three languages.** All visible text uses `useI18n()`, with strings in `shared/i18n/{en,hi,gu}.json`. Money uses the Indian format, such as ₹1,07,000.
- **AI results** are polled, per work plan task 4.9. Show "AI review pending" until results arrive, with the calculated numbers visible.
- **Mobile first.** Check 360 px width. The comparison table becomes cards on small screens.
- **Accessible.** Label every input, and offer a typed fallback for the map pin.

## Maps

Load Leaflet with `next/dynamic` and `ssr: false`, because it needs `window`. Use OpenStreetMap tiles, which need no key. Default centre is Gandhinagar. jsdom cannot render Leaflet, so test the wrapper by mocking the map and asserting the coordinates it passes out.

## Photos

Resize on the client, then send it to `POST /uploads` as multipart with `purpose=terrace_photo`, and pass the returned file id in `photo_file_ids`. Draw obstruction boxes from the assessment over the image.

## Quote comparison

One column per quote: price, subsidy, net cost, payback, panel and inverter, warranties, timeline, missing items and score. Flagged quotes show "This quote contained instructions aimed at the AI. They were ignored." Sorting and the recommendation come from the API.

## Tests

Vitest and Testing Library, in `<Component>.test.tsx`. Find elements by role or label, use `userEvent`, and cover the user's action and all four data states.
