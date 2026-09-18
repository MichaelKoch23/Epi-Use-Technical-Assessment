# Employee Hierarchy Management System

A cloud-hosted web application for managing EPI-USE Africa's employee records and reporting hierarchy - built as the Technical Services internship assessment.

The system is a single-page React application (`web/`) backed by a stateless FastAPI REST API (`api/`) and a PostgreSQL database. It provides full CRUD over employee records, an interactive and searchable organisational chart, a sortable and filterable reporting table, and Gravatar-based avatars, plus role-based access control with salary confidentiality, a full audit trail, CSV import/export, and organisational analytics.

Reporting lines are **effective-dated**: every change is recorded with the date it takes effect, so the organisation can be read as at any past date and a move can be scheduled to take effect on its own in the future.

## Documentation

| Document | For |
|---|---|
| [docs/USER-GUIDE.md](docs/USER-GUIDE.md) | Using the system - written for people with no technical background |
| [docs/TECHNICAL-DESIGN.md](docs/TECHNICAL-DESIGN.md) | How it is built and why; architecture, data design, security, decision register |
| [docs/DEPLOY-RUNBOOK.md](docs/DEPLOY-RUNBOOK.md) | Running, migrating, deploying, rolling back and triaging it |

## Project structure

```
api/      FastAPI backend (SQLAlchemy models, Alembic migrations, services, routers)
web/      React frontend
docs/     Technical design, user guide, deploy runbook, brand style guide
scripts/  dev.sh (run it), check.sh (lint/type/test/build gate), migrate.sh (Alembic)
```

## Getting started

The database is a managed PostgreSQL branch, not a local container, so configuration comes first.

```bash
cp .env.example .env     # fill in DATABASE_URL and JWT_SECRET
bash scripts/migrate.sh dev # apply migrations
bash scripts/dev.sh         # build and run the production image on :8080
```

`JWT_SECRET` needs at least 32 characters of real entropy (`openssl rand -hex 32`); the application refuses to start on a weak one.

To generate a demo organisation of roughly 250 people, with eighteen months of reporting history and a few scheduled changes:

```bash
cd api && uv run python -m app.seed --employees 250 --reset
```

Full instructions, including the frontend dev server and deployment, are in the [deploy runbook](docs/DEPLOY-RUNBOOK.md).

## Checks

```bash
bash scripts/check.sh
```

Runs Ruff, mypy and pytest over the API; `tsc`, oxlint and Vitest over the frontend; the Vite production build; and finally a build of the production container image.

## License

MIT - see [LICENSE](LICENSE).
