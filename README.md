# Employee Hierarchy Management System

A cloud-hosted web application for managing EPI-USE Africa's employee records and reporting hierarchy - built as the Technical Services internship assessment.

The system is a single-page React application (`web/`) backed by a stateless FastAPI REST API (`api/`) and a PostgreSQL database. It provides full CRUD over employee records, an interactive and searchable organisational chart, a sortable and filterable reporting table and Gravatar-based avatars, plus role-based access control with salary confidentiality, a full audit trail, CSV import/export and organisational analytics.

## Live application

**<https://ehm-351897716342.europe-west3.run.app>**

| Sign in as | Email | Password | Sees |
|---|---|---|---|
| Administrator | `admin@example.com` | `Demo-Admin-2026!` | Everything, including salaries |
| Read-only | `viewer@example.com` | `Demo-Viewer-2026!` | No salary figures anywhere |

Both are seeded demo accounts on a throwaway database. Sign in as the viewer once: the salary column, the payroll figures on the analytics page and the salary column in an export are all *absent* rather than hidden, because the server never sends them.

Deployed on Google Cloud Run (`europe-west3`) against Neon PostgreSQL 18, from the `Dockerfile` in this repository.

Reporting lines are **effective-dated**: every change is recorded with the date it takes effect, so the organisation can be read as at any past date and a move can be scheduled to take effect on its own in the future.

## Documentation

| Document | For |
|---|---|
| [User Manual](docs/USER-GUIDE.pdf) | Using the system - written for people with no technical background |
| [Technical Document](docs/TECHNICAL-DESIGN.pdf) | How it is built and why, architecture, data model, hierarchy validity, security, deployment |

## Project structure

```
api/      FastAPI backend (SQLAlchemy models, Alembic migrations, services, routers)
web/      React frontend
docs/     Technical document and user manual (PDF)
scripts/  dev.sh (run it), check.sh (lint/type/test/build gate), migrate.sh (Alembic)
```

## Getting started

The database is a managed PostgreSQL branch, not a local container, so configuration comes first.

```bash
cp .env.example .env     # fill in DATABASE_URL and JWT_SECRET
bash scripts/migrate.sh dev # apply migrations
bash scripts/dev.sh         # build and run the production image on :8080
```

`JWT_SECRET` needs at least 32 characters of real entropy (`openssl rand -hex 32`), the application refuses to start on a weak one.

To generate a demo organisation of roughly 250 people, with eighteen months of reporting history and a few scheduled changes:

```bash
cd api && uv run python -m app.seed --employees 250 --reset
```

For frontend hot reload, run `npm run dev` in `web/` alongside the container, the container on `:8080` stays the reference for whether a change is actually done. How the deployed service is put together - Cloud Run, the managed database, secrets and the release path - is described in section 2.6 of the [technical document](docs/TECHNICAL-DESIGN.pdf).

## Checks

```bash
bash scripts/check.sh
```

Runs Ruff, mypy and pytest over the API, `tsc`, oxlint and Vitest over the frontend, the Vite production build and finally a build of the production container image.
