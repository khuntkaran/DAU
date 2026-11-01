---
name: add-api-endpoint
description: Add or change a FastAPI endpoint in api/ with the project's layering, validation, authorization and tests. Use for any work on routers, services, authentication, uploads or SSE.
argument-hint: "[METHOD /path and purpose]"
---

# Add an API endpoint

Target: $ARGUMENTS

The API surface is section 08 of `SuryaSetu Architecture.html`. Work in this order, tests first.

1. **Schemas.** Add request and response Pydantic models to `api/app/schemas.py`.
2. **Test.** Add to `api/tests/test_<module>.py` with FastAPI's `TestClient` on a temporary SQLite database. Cover success, invalid input (422), not signed in (401), wrong role or another user's data (403 or 404), and state conflicts (409). Run it and see it fail.
3. **Service.** `api/app/services/<module>.py` holds rules and transactions, with no FastAPI imports. Calculations come from `rules`.
4. **Router.** `api/app/routers/<module>.py` does dependency injection and the service call only.
5. **Register** it in `api/app/main.py`.
6. **Regenerate** the contract with `npm run api:openapi`; the web types are generated from `api/openapi.json`.

## Rules

- Every route declares its role dependency, or is explicitly public.
- Check ownership in the service.
- Errors use one shape: `{ "error": { "code", "message", "details" } }`.
- The API never waits on an LLM. It creates a job and returns `202` with the job id.
- Lists are paginated. `GET /requests/open` takes `bbox` and filters by service radius.
- Vendor responses use a location rounded to about 500 m and no phone number until accepted. Use a separate response model, and test it.

## States

```
Request: draft → open → quoted → accepted → completed
         open or quoted → cancelled or expired
Quote:   draft → submitted → revised → accepted | rejected | withdrawn | expired
```

Accept runs in one transaction: lock the request (`SELECT … FOR UPDATE` on PostgreSQL; SQLite serialises writers), confirm it is `quoted`, accept the quote, reject the others, mark the request `accepted`, then publish the SSE events after commit. The partial unique index on accepted quotes is the final guard. Test two simultaneous accepts, and expect one 200 and one 409.

## Uploads

`POST /uploads` takes a multipart file and a `purpose`, saves it under `UPLOAD_DIR`, and records a `files` row with its sha256. `schemas.check_upload` restricts type and size, and the server confirms the file signature before use. Production swaps this for presigned object storage.
