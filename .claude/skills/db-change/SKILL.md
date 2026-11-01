---
name: db-change
description: Change the PostgreSQL schema with SQLAlchemy and Alembic, including tables, columns, PostGIS indexes, constraints, migrations and seed data. Use for any database structure change in api/.
argument-hint: "[what is changing]"
---

# Change the database

Change: $ARGUMENTS

1. Edit `api/app/models.py`.
2. Run `npm run db:revision -- "message"`, then read the generated migration. Autogenerate misses some PostGIS and partial index details.
3. Add a test that exercises the new structure or constraint.
4. Run `npm run db:migrate` and `npm run test`.
5. Check that downgrade works.
6. Update `seed/seed.py` if the change affects it.

## Rules

- Committed migrations are never edited. A hook blocks this.
- Primary keys are UUIDs. Every table has `created_at`, and mutable tables have `updated_at`.
- Money is `Integer` rupees. Capacity is `Numeric(6, 2)` kW. Never use `Float` for money.
- Index every foreign key and every filter column.
- Enforce invariants in the database as well as in code.

## Required indexes

From section 07 of `SuryaSetu Architecture.html`:

- GiST on `solar_requests.location`, partial on `status IN ('OPEN', 'QUOTED')`
- Unique `(request_id, vendor_id)` on `quotes`
- Partial unique on `quotes (request_id) WHERE status = 'ACCEPTED'`
- `ai_jobs (input_hash, type)` for deduplication

## Tables

`users`, `vendors`, `solar_requests`, `request_media`, `quotes`, `quote_reviews`, `recommendations`, `ai_jobs`, `rule_sets`. Fields are in the design document. `location` and `base_point` are PostGIS `geography(Point, 4326)`. AI output is JSONB.
