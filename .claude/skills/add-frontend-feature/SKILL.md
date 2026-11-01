---
name: add-frontend-feature
description: Build a household or vendor screen or component in web/ with Next.js, Tailwind and tests. Use for any React, Tailwind, Leaflet map, photo upload, quote comparison, voice UI or translation work.
argument-hint: "[feature or screen]"
---

# Add a frontend feature

Target: $ARGUMENTS

## Structure

```
web/app/(household)/      Household routes
web/app/(vendor)/         Vendor routes
web/components/           Shared components, each with a .test.tsx
web/lib/api-types.ts      Generated from OpenAPI, never edited
web/lib/api.ts            Typed client
web/i18n/{en,hi,gu}.json
```

## Rules

- **Tailwind only**, with colours from the theme tokens in `web/app/globals.css`. No other UI kit and no hard-coded hex values in components.
- **Server Components by default.** Add `"use client"` only for interaction, the map, recording or SSE.
- **Generated types only.** Run `npm run api:types` after an API change.
- **Every data screen handles** loading, error with retry, empty and success.
- **No business maths in the browser.** Subsidy, payback and scores come from the API, with an ⓘ source link from `<RuleSources />`.
- **Three languages.** All visible text uses `next-intl`, with strings in `en`, `hi` and `gu`. Money uses the Indian format, such as ₹1,07,000.
- **Live updates** come from `GET /events` (SSE), with `GET /jobs/{id}` polling as the fallback. Show "AI review pending" until results arrive, with the calculated numbers visible.
- **Mobile first.** Check 360 px width. The comparison table becomes cards on small screens.
- **Accessible.** Label every input, and offer a typed fallback for the map pin.

## Maps

Load Leaflet with `next/dynamic` and `ssr: false`, because it needs `window`. Use OpenStreetMap tiles, which need no key. Default centre is Gandhinagar. jsdom cannot render Leaflet, so test the wrapper by mocking the map and asserting the coordinates it passes out.

## Photos

Resize on the client, request a presigned URL, and PUT directly to storage. Draw obstruction boxes from the assessment over the image.

## Quote comparison

One column per quote: price, subsidy, net cost, payback, panel and inverter, warranties, timeline, missing items and score. Flagged quotes show "This quote contained instructions aimed at the AI. They were ignored." Sorting and the recommendation come from the API.

## Tests

Vitest and Testing Library, in `<Component>.test.tsx`. Find elements by role or label, use `userEvent`, and cover the user's action and all four data states.
