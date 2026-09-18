# Deploy Runbook

Operational procedures for the Employee Hierarchy Management System: how to get it running, how to change it safely, and what to do when it misbehaves.

This is the *how*. For the *why* - topology, connection budgeting, revision strategy - see [TECHNICAL-DESIGN.md section 10](TECHNICAL-DESIGN.md#10-deployment-and-operations).

> **Status.** Deployment is currently run by hand from a workstation. There is no CI/CD pipeline in the repository ([section 10.6](TECHNICAL-DESIGN.md#106-cicd-and-migrations)), so every procedure below is written as something a person executes and can verify.

---

## Contents

1. [What you need](#1-what-you-need)
2. [Configuration](#2-configuration)
3. [Running it locally](#3-running-it-locally)
4. [Seeding a demo organisation](#4-seeding-a-demo-organisation)
5. [Migrations](#5-migrations)
6. [Deploying](#6-deploying)
7. [Rolling back](#7-rolling-back)
8. [Health checks and triage](#8-health-checks-and-triage)
9. [Routine operations](#9-routine-operations)

---

## 1. What you need

| Tool | Used for | Needed where |
|---|---|---|
| Docker (with Compose) | Building and running the image | Local, deploy |
| [`uv`](https://docs.astral.sh/uv/) | Python dependency management, Alembic, the seeder | Local, migrations |
| Node 22+ | Frontend dev server and the type generator | Local frontend work only |
| [Neon CLI](https://neon.com/docs/reference/neon-cli) (`neon`) | Resolving branch connection strings for migrations | Migrations |
| `gcloud` | Cloud Run deploys | Deploy |

The Neon project is recorded in `.neon` at the repository root (project `wild-surf-18764091`, default branch `dev`). `scripts/migrate.sh` reads the same project id.

---

## 2. Configuration

Copy the template and fill in the two variables that have no default:

```bash
cp .env.example .env
```

| Variable | Notes |
|---|---|
| `DATABASE_URL` | The **pooled** Neon connection string for the application. Migrations use a direct one instead - `scripts/migrate.sh` resolves that itself and refuses a pooled URL. |
| `JWT_SECRET` | `openssl rand -hex 32`. Under 32 characters, or a well-known value like `changeme`, and the application **refuses to start**. |

Everything else has a working default; the full list is [Appendix B](TECHNICAL-DESIGN.md#appendix-b---configuration).

### `DATABASE_URL` is not what the Neon console hands you

Neon's **Connect** dialog gives a string for `psql`. The application drives
PostgreSQL through SQLAlchemy's **asyncpg** dialect, which needs three changes to
it. Miss any one and the container starts and then fails on its first query:

| Neon gives you | Store this |
|---|---|
| `postgresql://` | `postgresql+asyncpg://` |
| `?sslmode=require&channel_binding=require` | `?ssl=require` |
| the plain host | the **`-pooler`** host (toggle *Connection pooling* on in the dialog) |

The result is one line:

```
postgresql+asyncpg://USER:PASSWORD@ep-xxxx-pooler.eu-central-1.aws.neon.tech/DBNAME?ssl=require
```

`sslmode` and `channel_binding` are libpq spellings. asyncpg does not accept
them and raises `connect() got an unexpected keyword argument 'sslmode'`, which
reads like a code fault and is in fact a configuration one. asyncpg spells the
same thing `ssl`.

Alembic is the exception and needs no thought: `alembic/env.py` rewrites
whatever it is given onto the synchronous `postgresql+psycopg` driver, and
`scripts/migrate.sh` resolves its own **direct** (non-pooled) string.

When storing the value in a secret manager, write it with `printf '%s'` rather
than `echo` - a trailing newline makes the URL unparseable.

Two settings are worth knowing before a production deploy:

- **`ENVIRONMENT=production`** switches off `/docs`, `/redoc` and `/openapi.json`, and adds an HSTS header. Anything else leaves them reachable.
- **`CORS_ORIGINS`** is not needed for the deployed service, where the SPA is served from the same origin as the API. Set it only when running the Vite dev server against a remote API. `*` is rejected outright, and in production plaintext `http://` origins are rejected too.

`.env` is git-ignored. It is the one file that must never be committed.

---

## 3. Running it locally

```bash
bash scripts/dev.sh
```

That is `docker compose up --build`: it builds the production image and runs it against whatever `DATABASE_URL` points at. **There is no local PostgreSQL container** - the database is a Neon branch. The application comes up on <http://localhost:8080>, serving both the API and the built SPA.

Running the real image locally is deliberate. The container under test is the container that ships, on a database with the same extensions (`pg_trgm`, `btree_gist`) and the same pooled-connection behaviour as production.

For frontend work with hot reload, run the Vite dev server alongside it:

```bash
cd web && npm install && npm run dev      # http://localhost:5173
```

The dev server proxies API calls to the container on :8080. **Re-check the container before calling a change done** - that is what ships; the dev server is a convenience.

### Before you push

```bash
bash scripts/check.sh
```

Lint, types, tests and the production image build, for both halves of the system, in one command. It is the gate: if it passes, the change is shippable.

One detail in that script is easy to undo by accident: the frontend type-check is `tsc -b`, not `tsc --noEmit`. `web/tsconfig.json` is a solution file with `"files": []`, so in non-build mode `tsc` type-checks nothing at all and passes unconditionally. Only build mode follows the project references to the configs that actually cover `src/`.

---

## 4. Seeding a demo organisation

```bash
cd api && uv run python -m app.seed --employees 250 --reset
```

`--reset` truncates `audit_log`, `employee_assignment` and `employee` first. **It does not ask for confirmation, and it does not check which database it is pointed at.** Check `DATABASE_URL` before running it with `--reset`.

The seeder writes through the same service layer the application uses, so every row is one the API would have produced. It creates roughly 250 people across five departments, spreads their opening reporting runs over the preceding eighteen months, and generates historical and future-dated moves - which is what gives the as-of controls and the scheduled-changes panel something real to show.

It also creates the two demo accounts (`admin@example.com`, `viewer@example.com`) and resets their passwords to the values in `app/seed.py`. Those are demo credentials for an assessment environment; they have no business being in a real deployment.

---

## 5. Migrations

```bash
bash scripts/migrate.sh dev      # the Neon 'dev' branch
bash scripts/migrate.sh prod     # the Neon 'main' branch - types 'prod' to confirm
```

The script resolves a connection string through the Neon CLI and **aborts if it gets a pooled one**, because `alembic upgrade head` over a transaction-mode pooler cannot hold the locks it needs. `prod` additionally demands a typed confirmation.

Migrations are **not** run from inside the container: `alembic/` is deliberately excluded from the image. Container start happens once per instance, and several instances starting at once would race to alter the same schema.

### Writing one

```bash
cd api && uv run alembic revision --autogenerate -m "describe the change"
```

**Always read the generated file before applying it.** Autogeneration does not see triggers, functions, partial indexes or exclusion constraints, all of which this schema uses - see `f3b91c5ad284` for what hand-written DDL in a migration looks like. Every model must be imported in `alembic/env.py`; one that is missing reads as a table to *drop*.

Migrations must be backward-compatible with the currently deployed application version, because the schema changes before traffic shifts. In practice: add columns nullable or with a default, and split a rename into add / backfill / deploy / drop across two releases.

### Verifying

```bash
cd api && uv run alembic current    # should print the head revision
```

---

## 6. Deploying

1. **Gate.** `bash scripts/check.sh` passes on the commit being deployed.
2. **Migrate.** `bash scripts/migrate.sh prod`, and confirm with `alembic current`.
3. **Build and push**, tagged with the commit SHA - never `latest`, so a revision is always traceable to a commit:

   ```bash
   SHA=$(git rev-parse --short HEAD)
   docker build -t "${REGISTRY}/ehm:${SHA}" .
   docker push "${REGISTRY}/ehm:${SHA}"
   ```

4. **Deploy with no traffic**, so the revision exists and can be checked before anyone reaches it:

   ```bash
   gcloud run deploy ehm --image "${REGISTRY}/ehm:${SHA}" --no-traffic --tag "rev-${SHA}"
   ```

5. **Smoke-test the tagged URL**: `/api/v1/health` returns `{"status":"ok","db":"ok"}`, then sign in and load the org chart.
6. **Shift traffic**, in a step rather than all at once:

   ```bash
   gcloud run services update-traffic ehm --to-tags "rev-${SHA}=10"
   # watch error rate and latency, then
   gcloud run services update-traffic ehm --to-latest
   ```

---

## 7. Rolling back

Cloud Run revisions are immutable, so a rollback is a traffic change, not a rebuild:

```bash
gcloud run revisions list --service ehm
gcloud run services update-traffic ehm --to-revisions "${PREVIOUS_REVISION}=100"
```

This takes seconds and needs no database restore **provided the migration in that release was backward-compatible** - which is exactly why section 5 requires it. A migration that dropped or renamed something the previous version reads cannot be rolled back this way; recovering from that means restoring the database, so the discipline in section 5 is what keeps rollback cheap.

---

## 8. Health checks and triage

`GET /api/v1/health` returns `{"status": "ok", "db": "ok"}` and touches the database, so a 200 means the API is up *and* can reach PostgreSQL. It is the container's startup probe.

| Symptom | Likely cause | Check |
|---|---|---|
| Container exits immediately at start | `JWT_SECRET` too short or well-known; `CORS_ORIGINS` contains `*`, or a plaintext origin in production | The validation error is printed on stdout and names the variable |
| Container starts, then every request 500s with `connect() got an unexpected keyword argument` | `DATABASE_URL` still carries libpq's `sslmode`/`channel_binding` | Rewrite it for asyncpg - see section 2 |
| `/health` 500s | Database unreachable, or the pool is exhausted | Neon compute suspended or at its connection limit; see below |
| Every request is slow on first hit after idle | Neon scale-to-zero, or a Cloud Run cold start | [section 10.8](TECHNICAL-DESIGN.md#108-cold-starts) - raise minimum instances |
| Requests hang, then time out | Connection pool exhausted (`pool_size=5, max_overflow=0`) | Long-running CSV exports hold a connection for the whole download; check for concurrent large exports |
| `/docs` returns 404 | Working as designed - `ENVIRONMENT=production` | Nothing to fix |
| Login always 429s | Rate limiter is seeing one client IP for everyone | The container must run with `--proxy-headers`; without it `X-Forwarded-For` is ignored |
| A scheduled move did not take effect | The cache column is refreshed on write and at start-up | Any write, or a restart, applies it; `SELECT sync_effective_assignments();` forces it |

**Connection budget.** Total connections are `max_instances x DB_POOL_SIZE`. Raising either without checking the other against Neon's limit is the standard way to cause an outage ([section 10.4](TECHNICAL-DESIGN.md#104-database-connections-under-autoscaling)).

**Logs.** The application does not emit structured logs or correlation ids ([section 10.7](TECHNICAL-DESIGN.md#107-observability)); you get Uvicorn's access lines in Cloud Logging, so tracing a report means matching on timestamp and path.

---

## 9. Routine operations

### Regenerate the frontend's API types after a contract change

```bash
cd web && npm run generate:api-types
```

This reads the live OpenAPI document and rewrites `src/lib/api-types.ts`. A contract change the frontend has not caught up with then fails `tsc` rather than at runtime. Commit the regenerated file with the change that caused it.

### Reset a forgotten demo password

**Do not re-run the seeder to do this.** It does reset the demo accounts' passwords, but it also generates a *second* complete organisation on top of the existing one - `--reset` is what stops that, and `--reset` truncates the employee data.

Set the hash directly instead:

```bash
cd api && uv run python -c "
from app.core.passwords import hash_password
print(hash_password('<new-password>'))
"
```

```sql
UPDATE app_user SET password_hash = '<hash>' WHERE email = 'admin@example.com';
```

### Force every session to sign in again

Revoke the outstanding refresh tokens:

```sql
UPDATE refresh_token SET revoked_at = now() WHERE revoked_at IS NULL;
```

Access tokens already issued remain valid until they expire - 15 minutes by default ([section 13](TECHNICAL-DESIGN.md#13-technology-decision-register), item 8). Shorten `JWT_ACCESS_TTL_SECONDS` if that window matters more than the round trips it costs.

### Check for orphaned employees

The analytics page lists **unreachable** employees - active people not connected to any top-level person. It should be empty. If it is not, someone's manager was removed without their reports being moved, and those people are missing from the org chart. Reassign them, or promote one to root.
