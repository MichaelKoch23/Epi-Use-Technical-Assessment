# Employee Hierarchy Management System

A cloud-hosted web application for managing EPI-USE Africa's employee records and reporting hierarchy - built as the Technical Services internship assessment.

The system is a single-page React application (`web/`) backed by a stateless FastAPI REST API (`api/`) and a PostgreSQL database. It provides full CRUD over employee records, an interactive and searchable organisational chart, a sortable and filterable reporting table, and Gravatar-based avatars, plus role-based access control with salary confidentiality, a full audit trail, CSV import/export, and organisational analytics.

See [docs/TECHNICAL-DESIGN.md](docs/TECHNICAL-DESIGN.md) for the full design rationale and [docs/USER-GUIDE.md](docs/USER-GUIDE.md) for usage instructions.

## Project structure

```
api/    FastAPI backend (SQLAlchemy models, Alembic migrations, services, routers)
web/    React frontend
docs/   Technical design, user guide, brand style guide
```

## Getting started

```bash
docker compose up
```

## License

MIT - see [LICENSE](LICENSE).
