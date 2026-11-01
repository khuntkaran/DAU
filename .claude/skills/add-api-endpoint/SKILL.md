---
name: add-api-endpoint
description: Add or change a FastAPI endpoint in api/ with the project's layering, validation, authorization and tests. Use for any work on routers, services, authentication, uploads or SSE.
argument-hint: "[METHOD /path and purpose]"
---

# Add an API endpoint

Target: $ARGUMENTS

The API surface is section 08 of `SuryaSetu Architecture.html`. Work in this order, tests first.

1. **Schemas.** Add request and response Pydantic models to `api/app/schemas.py`.
2. **Test.** Add to `api/tests/test_<module>.py` with `httpx.AsyncClient` against real Postgres. Cover success, invalid input (422), not signed in (401), wrong role or another user's data (403 or 404), and state conflicts (409). Run it and see it fail.
3. **Service.** `api/app/services/<module>.py` holds rules and transactions, with no FastAPI imports. Calculations come from `rules`.
4. **Router.** `api/app/routers/<module>.py` does dependency injection and the service call only.
5. **Register** it in `api/app/main.py`.
6. **Regenerate** web types with `npm run api:types`.

## Rules

- Every route declares its role dependency, or is explicitly public.
- Check ownership in the service.
- Errors use one shape: `{ "error": { "code", "message", "details" } }`.
- The API never waits on an LLM. It creates a job and returns `202` with the job id.
- Lists are paginated. `GET /requests/open` takes `bbox` and filters by service radius.
- Vendor responses use a location rounded to about 500 m and no phone number until accepted. Use a separate response model, and test it.

## States

```
Request: DRAFT → OPEN → QUOTED → ACCEPTED → INSTALLED (stretch)
         OPEN or QUOTED → CANCELLED or EXPIRED
Quote:   SUBMITTED → ACCEPTED | REJECTED | WITHDRAWN
```

Accept runs in one transaction: `SELECT … FOR UPDATE` on the request, confirm it is `QUOTED`, accept the quote, reject the others, mark the request `ACCEPTED`, then publish the SSE events after commit. Test two simultaneous accepts, and expect one 200 and one 409.

## Uploads

`POST /uploads/presign` returns a presigned PUT URL and object key, so the API never carries photo bytes. Restrict content type and size in the presigned policy. The worker confirms the file signature before use.
