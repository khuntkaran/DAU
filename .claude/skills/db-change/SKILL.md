---
name: db-change
description: Change the database schema with SQLAlchemy, including tables, columns, indexes, constraints and seed data. SQLite locally, PostgreSQL in production. Use for any database structure change in api/.
argument-hint: "[what is changing]"
---

# Change the database

Change: $ARGUMENTS

The tables and columns come from `docs/previous/db-schema.html`. Build P0 tables first; add P1 to P3 tables only when their feature is built.

1. Edit `api/app/models.py`, using the portable types in `api/app/db.py`.
2. Add a test in `api/tests/test_models.py` that exercises the new structure or constraint on SQLite.
3. Run `npm run test`.
4. Update the seed script if the change affects it, then rebuild the local database with `--reset`.

Alembic migrations start when production moves to PostgreSQL. Until then the seed script creates the tables.

## Rules

- Primary keys are `Uuid`. Every table has `created_at`, and mutable tables have `updated_at`.
- Money is `int` rupees. Capacity is `Numeric(5, 2)` kW. Never use `Float` for money.
- Status and type columns use `str_enum(...)` from `db.py`, storing the lowercase values in `api/app/enums.py`.
- JSON columns use `JsonDoc`, which becomes JSONB on PostgreSQL.
- Partial indexes set both `sqlite_where` and `postgresql_where`.
- Enforce invariants in the database as well as in code.

## Required constraints and indexes

- Unique `(request_id, vendor_id)` on `quotes`
- Partial unique on `quotes (request_id) WHERE status = 'accepted'`
- `solar_requests (status, lat, lng)` for the vendor map; production adds a GiST index on a PostGIS column
- `ai_jobs (input_hash, job_type)` for deduplication
- The rest are listed under "Keys, constraints and indexes" in `db-schema.html`
