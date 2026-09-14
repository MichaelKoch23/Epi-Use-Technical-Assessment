# Employee Hierarchy Management System
## Technical Design Document

| | |
|---|---|
| **Prepared for** | EPI-USE Africa - Technical Services Internship Assessment |
| **Author** | Michael Koch |
| **Version** | 1.0 |
| **Date** | «submission date» |
| **Live application** | «https://…» |
| **API documentation** | «https://…/docs» (interactive OpenAPI) |
| **Source repository** | «https://github.com/…» |
| **Demo credentials** | Admin: «…» · Read-only: «…» |

> Placeholders marked «…» must be filled before submission.

---

## 1. Executive summary

This document describes the design of a cloud-hosted web application that manages EPI-USE Africa's employee records and reporting hierarchy.

The system is a **single-page React application backed by a stateless REST API and a managed PostgreSQL database**. It provides full CRUD over employee records, an interactive and searchable organisational chart, a sortable and filterable reporting table, and Gravatar-based avatars. Beyond the brief it adds role-based access control with salary confidentiality, a full audit trail, CSV import/export, and organisational analytics.

Three decisions shape the design, and the rest of this document justifies them:

1. **PostgreSQL with an adjacency-list hierarchy and recursive CTEs.** The reporting structure is a rooted forest, and the hard part is not storing it but keeping it *provably acyclic* under concurrent edits. A relational database with transactional integrity, declarative constraints and recursive queries solves that directly; a document store does not.
2. **An explicit, versioned, self-documenting HTTP API.** The API is a first-class deliverable rather than an implementation detail of the UI. It is generated as an OpenAPI 3.1 specification from the same type definitions that validate requests at runtime, so the contract cannot drift from the code.
3. **Deploy on day one, then build.** The brief's non-negotiable is a working public URL. Continuous deployment from the first commit means deployment risk is retired early rather than discovered late.

---

## 2. Requirements

### 2.1 Functional requirements

| ID | Requirement | Source |
|---|---|---|
| FR-1 | Create, read, update and delete employee records | Brief |
| FR-2 | Record name, surname, birth date, employee number, salary, role/position and reporting line manager | Brief |
| FR-3 | Set and change an employee's reporting line manager | Brief |
| FR-4 | An employee may not be their own manager | Brief |
| FR-5 | An employee may have no manager (e.g. the CEO) | Brief |
| FR-6 | Present the hierarchy as a visual tree or graph | Brief |
| FR-7 | Search the hierarchy to find, edit or delete an employee | Brief |
| FR-8 | Provide a table/list view sortable and filterable on any employee field | Brief |
| FR-9 | Display Gravatar avatars linked to employee data | Brief |
| FR-10 | Optionally support avatar upload | Brief (nice-to-have) |
| FR-11 | Prevent indirect reporting cycles (A → B → C → A) | Derived from FR-4 |
| FR-12 | Define deletion behaviour for an employee who has direct reports | Derived from FR-1 |
| FR-13 | Role-based access with salary visibility restricted to authorised roles | Added |
| FR-14 | Audit trail of all data changes | Added |
| FR-15 | Bulk CSV/Excel import with validation, and full data export | Added |
| FR-16 | Organisational analytics (headcount, cost roll-up, span of control) | Added |

### 2.2 Non-functional requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | Publicly reachable over HTTPS from a single URL | 100% of assessment window |
| NFR-2 | All state persisted in a remote database; no hardcoded or file-based data | Absolute constraint |
| NFR-3 | Read latency for hierarchy and list views | p95 < 400 ms at 1 000 employees |
| NFR-4 | Hierarchy remains acyclic under concurrent writes | Enforced at database level |
| NFR-5 | Salary values never returned to unauthorised principals | Enforced server-side |
| NFR-6 | Automated test coverage on domain and service layers | ≥ 80% |
| NFR-7 | Reproducible builds and one-command local startup | `docker compose up` |
| NFR-8 | WCAG 2.1 AA for keyboard navigation and contrast | Audited via Lighthouse/axe |
| NFR-9 | Alignment with POPIA principles for personal information | Documented in §9.5 |

### 2.3 Requirements traceability

| Requirement | Implemented by | Verified by |
|---|---|---|
| FR-1, FR-2 | `EmployeeService`, `/api/v1/employees` | Integration tests `test_employee_crud.py` |
| FR-3 | `PUT /employees/{id}/manager`, `ReassignmentService` | `test_reassignment.py` |
| FR-4 | `CHECK (manager_id IS DISTINCT FROM id)` | `test_self_manager_rejected` |
| FR-5 | Nullable `manager_id`; `GET /hierarchy/roots` | `test_root_employee` |
| FR-6 | `OrgChart` component (React Flow + Dagre) | Manual + Playwright smoke test |
| FR-7 | `GET /search`, command palette, chart focus mode | `test_search.py` |
| FR-8 | `GET /employees` with whitelisted sort/filter params | `test_list_filtering.py` |
| FR-9 | `GravatarAdapter` (SHA-256 email hash) | `test_gravatar.py` |
| FR-11 | Deferred constraint trigger + service pre-check | `test_cycle_prevention.py` |
| FR-12 | `DeletionPolicy` strategy | `test_deletion_policies.py` |
| FR-13 | RBAC dependency + response schema selection | `test_salary_redaction.py` |
| FR-14 | `AuditLog` written inside the unit of work | `test_audit_trail.py` |

---

## 3. Architecture

### 3.1 Architectural style

The solution is a **client–server application composed of a single-page application and a stateless HTTP API over a managed relational database**. Internally the API is a **layered modular monolith**: a single deployable unit whose modules (employees, hierarchy, auth, audit, analytics, import/export) are separated by explicit interfaces rather than by network boundaries.

It is worth being precise about what this architecture is *not*, because these labels are commonly misapplied:

- **Not microservices.** There is one deployable API with one database schema and one transactional boundary. Splitting it would introduce distributed-transaction problems for an invariant (acyclicity) that must be enforced atomically.
- **Not event-driven.** Communication is synchronous request/response. The optional outbound webhooks (§10.6) are a notification mechanism layered on top of synchronous writes, not an event-sourced or message-brokered core.
- **Not serverless-first in design, though serverless in deployment.** The API is a conventional ASGI application; the hosting platform happens to execute it as a function. The application makes no assumptions about instance lifetime, which is why connection pooling is externalised (§10.3).

This choice is deliberate. For a bounded domain with a single strong consistency requirement and a one-week delivery window, a modular monolith gives the strongest correctness guarantees at the lowest operational cost. The module boundaries are drawn so that extraction into separate services remains possible if the domain later warranted it.

### 3.2 System context

```mermaid
graph LR
    U[HR Administrator / Viewer]
    S[Employee Hierarchy<br/>Management System]
    G[Gravatar<br/>avatar + profile API]
    D[(Neon PostgreSQL<br/>managed database)]

    U -->|HTTPS| S
    S -->|HTTPS, read-only| G
    S -->|TLS, pooled| D
```

### 3.3 Container view

```mermaid
graph TD
    subgraph Browser
        SPA[React SPA<br/>TypeScript · Vite · Tailwind<br/>TanStack Query · React Flow]
    end

    subgraph "Vercel edge + functions"
        CDN[Static asset CDN]
        API[FastAPI application<br/>Python 3.12 · Pydantic v2 · SQLAlchemy 2.0]
    end

    DB[(Neon PostgreSQL 16<br/>pooled connection)]
    GRV[Gravatar CDN]
    BLOB[Object storage<br/>optional avatar uploads]

    SPA -->|static| CDN
    SPA -->|JSON over HTTPS<br/>/api/v1/*| API
    SPA -->|img src| GRV
    API --> DB
    API --> BLOB
    API -->|profile enrichment| GRV
```

### 3.4 API component view

```mermaid
graph TD
    R[Routers<br/>HTTP concerns only]
    DEP[Dependencies<br/>auth, RBAC, session, pagination]
    SVC[Services<br/>business rules and invariants]
    REPO[Repositories<br/>query construction]
    MOD[SQLAlchemy models<br/>+ Alembic migrations]
    ADP[Adapters<br/>Gravatar, storage, CSV]
    DBX[(PostgreSQL)]

    R --> DEP
    R --> SVC
    SVC --> REPO
    SVC --> ADP
    REPO --> MOD
    MOD --> DBX
```

**Layer responsibilities and rules:**

| Layer | Responsibility | May not |
|---|---|---|
| Router | Parse and validate HTTP input, select response schema, map domain exceptions to status codes | Contain business rules or touch the session directly |
| Dependency | Authenticate, authorise, open the unit of work, parse pagination | Perform writes |
| Service | Enforce invariants, orchestrate transactions, emit audit records | Know about HTTP |
| Repository | Build and execute queries, return domain objects | Enforce business rules |
| Adapter | Wrap external systems behind a narrow port | Leak vendor types upward |

The one-directional dependency rule means the domain and service layers are testable without a web server, and the Gravatar integration is replaceable with a fake in tests.

### 3.5 Request lifecycle - reassigning a manager

1. The user drags an employee card onto a new manager in the org chart.
2. The SPA optimistically updates its cache and issues `PUT /api/v1/employees/{id}/manager` with `If-Match: "<version>"`.
3. A FastAPI dependency validates the JWT and asserts the `hr_admin` role.
4. A second dependency opens a database session and begins a transaction.
5. `ReassignmentService` locks the employee row (`SELECT … FOR UPDATE`), checks the optimistic-lock version, then runs the subtree query of §4.6 to confirm the proposed manager is not a descendant.
6. The update is applied and an `audit_log` row is written in the same transaction.
7. The deferred acyclicity trigger re-validates at `COMMIT`, closing the race window described in §5.2.
8. The router returns `200 OK` with the new version; on conflict it returns `409` and the SPA rolls the optimistic update back and refetches.

---

## 4. Data design

### 4.1 Domain model

The domain has one aggregate root, `Employee`, which owns its identity, personal data, remuneration and its single reporting edge. The organisation as a whole is a **rooted forest**: every employee has at most one manager, and one or more employees have none.

Deliberate modelling choices:

- **Position is a string field, not a separate `Role` entity.** The brief asks for a role/position on the employee record. Normalising it into a table would add a join and a management screen for no requirement. This is noted as a roadmap item (§15) rather than pretended away.
- **`employee_number` is a natural key but not the primary key.** It is business-assigned, human-visible and potentially re-sequenced. A surrogate UUID primary key keeps foreign keys stable if numbering policy changes.
- **UUIDv7 rather than UUIDv4.** UUIDv7 is time-ordered, which preserves B-tree index locality on insert and avoids the write amplification of random UUIDs, while remaining non-enumerable in URLs.

### 4.2 Entity-relationship diagram

```mermaid
erDiagram
    EMPLOYEE ||--o{ EMPLOYEE : "manages"
    EMPLOYEE ||--o{ AUDIT_LOG : "is subject of"
    APP_USER ||--o{ AUDIT_LOG : "performs"

    EMPLOYEE {
        uuid id PK
        text employee_number UK
        text first_name
        text last_name
        text email UK
        date birth_date
        text position
        numeric salary
        char currency
        uuid manager_id FK
        text avatar_override_url
        int version
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    APP_USER {
        uuid id PK
        text email UK
        text password_hash
        text role
        timestamptz created_at
    }

    AUDIT_LOG {
        uuid id PK
        uuid employee_id FK
        uuid actor_id FK
        text action
        jsonb before
        jsonb after
        timestamptz occurred_at
    }
```

### 4.3 Choosing a hierarchy representation

This is the central data-design decision, so the alternatives are set out in full.

| Option | Read cost | Write cost | Integrity | Verdict |
|---|---|---|---|---|
| **Adjacency list + recursive CTE** | One recursive query per subtree | O(1) - update one column | Self-reference prevented declaratively; cycles prevented by trigger | **Selected** |
| Materialised path (`/ceo/cto/eng/`) | Very fast prefix scan | O(subtree) - rewrite every descendant path | Cycles impossible by construction, but paths can desynchronise | Rejected |
| Closure table (ancestor/descendant pairs) | Fastest - single indexed join | O(ancestors × descendants) rows rewritten per move | Strong, but duplicated state to keep consistent | Rejected at this scale |
| `ltree` extension | Fast, with operators and GiST indexing | Same rewrite cost as materialised path | Good, but extension-dependent | Rejected |
| Graph database (Neo4j) | Excellent traversal | Good | Excellent for traversal; weak for the tabular reporting view | Rejected |

**Rationale.** The workload is write-light and read-moderate at an organisational scale measured in thousands, not millions. Recursive CTEs in PostgreSQL resolve a 5 000-node subtree in single-digit milliseconds with an index on `manager_id`. Every alternative buys read speed the system does not need by paying in derived state that can drift from the truth - and drift is precisely the failure mode this domain cannot tolerate. The adjacency list keeps exactly one authoritative representation of the reporting edge.

The graph database deserves a word, because a reporting structure is a natural graph. It was rejected because the structure here is the *simple* case of a graph - a single-parent forest - which relational databases handle natively, while the brief's tabular reporting, sorting and filtering requirements are where relational databases are strongest and graph databases weakest. Adopting Neo4j would optimise the easy half of the problem and complicate the hard half.

If the system later needed sub-millisecond ancestor lookups across a million rows, the migration path is to add a closure table as a derived read model maintained by trigger, leaving the adjacency list authoritative.

### 4.4 Schema

```sql
CREATE TABLE employee (
    id                  UUID PRIMARY KEY,
    employee_number     TEXT        NOT NULL,
    first_name          TEXT        NOT NULL,
    last_name           TEXT        NOT NULL,
    email               TEXT        NOT NULL,
    birth_date          DATE        NOT NULL,
    position            TEXT        NOT NULL,
    salary              NUMERIC(12,2) NOT NULL,
    currency            CHAR(3)     NOT NULL DEFAULT 'ZAR',
    manager_id          UUID        REFERENCES employee(id) ON DELETE SET NULL,
    avatar_override_url TEXT,
    version             INTEGER     NOT NULL DEFAULT 1,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    deleted_at          TIMESTAMPTZ,

    CONSTRAINT employee_not_own_manager CHECK (manager_id IS DISTINCT FROM id),
    CONSTRAINT employee_salary_non_negative CHECK (salary >= 0),
    CONSTRAINT employee_birth_date_sane CHECK (birth_date > DATE '1900-01-01')
);

CREATE UNIQUE INDEX uq_employee_number ON employee (employee_number)
    WHERE deleted_at IS NULL;
CREATE UNIQUE INDEX uq_employee_email  ON employee (lower(email))
    WHERE deleted_at IS NULL;
CREATE INDEX ix_employee_manager       ON employee (manager_id)
    WHERE deleted_at IS NULL;
CREATE INDEX ix_employee_name_trgm     ON employee
    USING GIN ((first_name || ' ' || last_name) gin_trgm_ops);
```

Two details worth noting:

- **`IS DISTINCT FROM` rather than `<>`.** A plain `manager_id <> id` evaluates to `NULL` when `manager_id` is `NULL`, and a `CHECK` constraint passes on `NULL`. It would work by accident here, but `IS DISTINCT FROM` states the intent unambiguously and is correct for all inputs.
- **Birth date "not in the future" is enforced in the application, not the schema.** `CURRENT_DATE` is not immutable; embedding it in a `CHECK` constraint produces a predicate whose truth changes over time, which can make a valid backup impossible to restore. The schema constrains only what is time-invariant; the temporal rule lives in the Pydantic validator, where it is also testable.
- **Partial unique indexes** (`WHERE deleted_at IS NULL`) allow an employee number to be reused after a soft delete without weakening uniqueness among active records.

### 4.5 Soft deletion

Employee records are soft-deleted by default (`deleted_at` set) rather than physically removed. Personnel data has audit and compliance value, accidental deletion in a hierarchy is destructive, and a restore path is cheap to provide. A hard-delete endpoint exists for genuine erasure requests (§9.5), and it cascades the audit rows explicitly rather than silently.

### 4.6 Key queries

**Full subtree with depth, and a defensive cycle guard:**

```sql
WITH RECURSIVE subtree AS (
    SELECT e.*, 0 AS depth, ARRAY[e.id] AS path
    FROM employee e
    WHERE e.id = :root_id AND e.deleted_at IS NULL
  UNION ALL
    SELECT c.*, s.depth + 1, s.path || c.id
    FROM employee c
    JOIN subtree s ON c.manager_id = s.id
    WHERE c.deleted_at IS NULL
      AND NOT c.id = ANY(s.path)          -- terminates even on corrupt data
)
SELECT * FROM subtree ORDER BY depth, last_name;
```

**Reporting-line (ancestor chain) for breadcrumbs and chart focus mode:**

```sql
WITH RECURSIVE line AS (
    SELECT e.id, e.manager_id, 0 AS level
    FROM employee e WHERE e.id = :employee_id
  UNION ALL
    SELECT m.id, m.manager_id, l.level + 1
    FROM employee m JOIN line l ON m.id = l.manager_id
    WHERE l.level < 100
)
SELECT * FROM line WHERE level > 0 ORDER BY level;
```

**Cycle safety check before reassignment** - the proposed manager must not be inside the employee's own subtree:

```sql
SELECT NOT EXISTS (
    WITH RECURSIVE subtree AS (
        SELECT id FROM employee WHERE id = :employee_id
      UNION ALL
        SELECT c.id FROM employee c JOIN subtree s ON c.manager_id = s.id
    )
    SELECT 1 FROM subtree WHERE id = :new_manager_id
) AS is_safe;
```

**Cost and headcount roll-up for any branch** (powers the analytics panel):

```sql
SELECT count(*) AS headcount,
       sum(salary) AS total_annual_cost,
       round(avg(salary), 2) AS average_salary,
       max(depth) AS depth_below
FROM subtree;
```

---

## 5. Business rules and invariants

### 5.1 The invariants

| # | Invariant | Enforcement |
|---|---|---|
| I-1 | An employee is never their own manager | `CHECK` constraint (database) |
| I-2 | The reporting structure contains no cycles of any length | Deferred constraint trigger + service pre-check |
| I-3 | A manager reference always points to an existing, non-deleted employee | Foreign key + partial index |
| I-4 | Employee number and email are unique among active employees | Partial unique indexes |
| I-5 | Concurrent edits cannot silently overwrite one another | Optimistic lock on `version` |
| I-6 | Every mutation is attributable to a principal and a timestamp | Audit write inside the same transaction |

### 5.2 Cycle prevention, and why the obvious approach is not enough

The naive implementation checks "is the new manager inside this employee's subtree?" in application code and then writes. That check is correct in isolation and **wrong under concurrency**. Two simultaneous reassignments - A moved under B, and B moved under A - can each pass their own check against a snapshot that predates the other, and commit a cycle that neither request could have created alone.

Three layers address this:

1. **Row-level locking.** The service takes `SELECT … FOR UPDATE` on the employee and the proposed manager before validating, serialising conflicting moves on the same rows.
2. **A deferred constraint trigger.** Validation is re-run at `COMMIT`, after all statements in the transaction have been applied, so a cycle assembled from several statements is still caught.
3. **A defensive path guard in every recursive read** (`NOT id = ANY(path)`), so that even if corrupt data somehow existed, reads terminate rather than looping.

```sql
CREATE OR REPLACE FUNCTION assert_no_reporting_cycle() RETURNS trigger AS $$
DECLARE
    cursor_id UUID := NEW.manager_id;
    hops      INT  := 0;
BEGIN
    WHILE cursor_id IS NOT NULL LOOP
        IF cursor_id = NEW.id THEN
            RAISE EXCEPTION 'Reporting cycle detected for employee %', NEW.id
                USING ERRCODE = 'check_violation';
        END IF;
        SELECT manager_id INTO cursor_id FROM employee WHERE id = cursor_id;
        hops := hops + 1;
        IF hops > 1000 THEN
            RAISE EXCEPTION 'Reporting chain exceeds maximum supported depth';
        END IF;
    END LOOP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE CONSTRAINT TRIGGER employee_no_cycle
    AFTER INSERT OR UPDATE OF manager_id ON employee
    DEFERRABLE INITIALLY DEFERRED
    FOR EACH ROW EXECUTE FUNCTION assert_no_reporting_cycle();
```

The service-layer pre-check is not redundant with the trigger: it exists to return a clear, actionable `422` with the name of the offending employee, rather than surfacing a database exception to the user.

### 5.3 Deleting an employee who has direct reports

The brief does not specify what happens to an employee's reports when that employee is removed, which makes it a design decision rather than an omission. Three policies are implemented behind a **strategy interface**, selected per request:

| Policy | Behaviour | Default for |
|---|---|---|
| `reparent` | Direct reports are reassigned to the deleted employee's manager | Ordinary departures - preserves the chain |
| `promote_to_root` | Direct reports become managerless and appear as new roots | Removing a root, or restructuring |
| `cascade` | The entire subtree is soft-deleted | Closing a whole department |

The UI never applies `cascade` silently: it requests a preview first, showing the exact count and names of affected employees, and requires explicit confirmation. Deleting a root with `reparent` degrades gracefully to `promote_to_root`, since there is no grandparent to reparent to.

### 5.4 Concurrency control

Every write carries the record's `version`, supplied as an `If-Match` header. A mismatch returns `409 Conflict` with both the client's stale representation and the current server state, so the UI can present a meaningful "this record changed while you were editing" dialogue rather than discarding one user's work. Pessimistic locking was rejected: lock lifetime across a human editing session is unbounded, and conflicts in this domain are rare enough that optimistic control is the better trade.

---

## 6. API design

### 6.1 Principles

Resource-oriented, versioned under `/api/v1`, JSON only, no verbs in paths. State-changing operations that carry their own business rules get a dedicated sub-resource rather than being folded into a general `PATCH`, because their authorisation, validation and audit semantics differ.

### 6.2 Endpoints

| Method | Path | Purpose | Role |
|---|---|---|---|
| `POST` | `/auth/login` | Exchange credentials for access + refresh tokens | Public |
| `POST` | `/auth/refresh` | Rotate refresh token | Authenticated |
| `GET` | `/auth/me` | Current principal and capability flags | Authenticated |
| `GET` | `/employees` | Paginated list; sort, filter, free-text search | Viewer |
| `POST` | `/employees` | Create employee | Admin |
| `GET` | `/employees/{id}` | Single employee with manager and direct reports | Viewer |
| `PATCH` | `/employees/{id}` | Partial update (optimistic lock) | Admin |
| `DELETE` | `/employees/{id}` | Soft delete with `?policy=` | Admin |
| `POST` | `/employees/{id}/restore` | Undo a soft delete | Admin |
| `GET` | `/employees/{id}/deletion-preview` | Affected records for a given policy | Admin |
| `PUT` | `/employees/{id}/manager` | Reassign reporting line | Admin |
| `GET` | `/employees/{id}/subtree` | Descendants to `?depth=` | Viewer |
| `GET` | `/employees/{id}/reporting-line` | Ancestor chain to the root | Viewer |
| `GET` | `/employees/{id}/audit` | Change history for one employee | Admin |
| `GET` | `/hierarchy/roots` | Employees with no manager | Viewer |
| `GET` | `/hierarchy/tree` | Chart-shaped payload, lazily expandable | Viewer |
| `GET` | `/analytics/org-summary` | Headcount, depth, span-of-control, anomalies | Viewer |
| `GET` | `/analytics/branch/{id}` | Cost and headcount roll-up for a branch | Admin |
| `POST` | `/imports/employees` | CSV/XLSX upload; `?dry_run=true` validates only | Admin |
| `GET` | `/exports/employees.csv` | Full extract honouring current filters | Viewer |
| `GET` | `/search` | Cross-entity quick search for the command palette | Viewer |
| `GET` | `/health` | Liveness and database reachability | Public |

### 6.3 List query contract

```
GET /api/v1/employees
    ?q=jansen                      # trigram fuzzy match on name, position, employee number
    &position=Integration+Architect
    &manager_id=<uuid>
    &min_salary=450000&max_salary=900000
    &hired_before=2024-01-01
    &sort=last_name&order=asc      # sort field validated against an allow-list
    &page=1&page_size=50
```

`sort` is resolved against a static map of permitted column names. Dynamic `ORDER BY` built from raw user input is the classic injection vector that parameterised queries do **not** protect against, because identifiers cannot be bound as parameters. Sorting and filtering are performed in the database, not in the browser, so the table view remains correct and fast when the dataset outgrows a single page.

### 6.4 Error model

All errors return `application/problem+json` per RFC 9457:

```json
{
  "type": "https://«host»/errors/reporting-cycle",
  "title": "Reassignment would create a reporting cycle",
  "status": 422,
  "detail": "Thandi Mokoena reports to Michael Koch indirectly and cannot become his manager.",
  "instance": "/api/v1/employees/018f.../manager",
  "errors": [{ "field": "manager_id", "code": "cycle_detected" }]
}
```

A single exception-handler layer maps domain exceptions to problem documents, so routers contain no error-formatting logic and messages stay consistent.

### 6.5 Contract documentation

FastAPI derives an OpenAPI 3.1 document from the same Pydantic models used for runtime validation, so the published contract cannot drift from the implementation. Swagger UI is served at `/docs` and ReDoc at `/redoc`, both publicly reachable for assessment. A Postman collection is generated from the specification and committed to the repository.

---

## 7. Frontend design

### 7.1 Structure

```
src/
  app/            routing, providers, error boundaries
  features/
    employees/    list view, detail drawer, forms
    hierarchy/    org chart, node renderers, layout
    analytics/    summary cards, distributions
    auth/         login, session, capability gates
  components/ui/  shadcn/ui primitives
  lib/            generated API client, hooks, formatters
```

Feature-first rather than type-first: everything needed to change the org chart lives in one directory, which keeps the module boundaries in the UI aligned with those in the API.

### 7.2 State management

Server state and client state are handled separately, which avoids the most common source of accidental complexity in data-heavy UIs.

- **Server state - TanStack Query.** Caching, deduplication, background refetch, optimistic updates and rollback are solved rather than reimplemented. Query keys are derived from the filter object, so changing a filter is a cache lookup rather than a manual refetch.
- **Client state - React state and URL search params.** Filters, sort order and the selected employee live in the URL, which makes every view shareable and bookmarkable and gives back/forward navigation for free.
- **A global store was deliberately not introduced.** Redux or Zustand would add a layer whose primary job - caching server data - is already covered.

### 7.3 Rendering the hierarchy

**React Flow with a Dagre layout pass** was selected over hand-rolled D3 and over off-the-shelf org-chart libraries. React Flow supplies pan, zoom, minimap, viewport virtualisation and drag interaction; Dagre computes a deterministic layered tree layout; node rendering stays as ordinary React components, so an employee card in the chart reuses the same avatar and badge components as the table view.

Behaviour at scale:

- The chart requests the tree lazily - roots plus two levels initially, then a subtree fetch on expand - so a 5 000-employee organisation does not serialise into a single response.
- **Focus mode** renders an employee's full ancestor chain plus a configurable depth of descendants, which is how people actually read an org chart.
- Searching selects and centres the matching node, expanding collapsed ancestors along the way.
- **Drag-and-drop reassignment**: dropping a card onto another employee issues the reassignment call. Invalid targets - the employee's own descendants - are computed client-side from the loaded subtree and shown as non-droppable *before* the drop, with the server remaining the authority.

### 7.4 Table view

TanStack Table in fully controlled mode, with sorting, filtering and pagination delegated to the server (§6.3). Column visibility is user-configurable and persisted per session; salary columns are absent entirely for unauthorised roles rather than hidden client-side.

### 7.5 Accessibility and responsiveness

Forms are built on Radix primitives via shadcn/ui, giving correct focus management, labelling and `aria` semantics. The chart, being inherently visual, has an equivalent accessible path: a keyboard-navigable nested-list view of the same hierarchy, which also serves as the print view. Colour is never the sole carrier of meaning. Target: Lighthouse accessibility ≥ 95 and zero critical axe violations.

---

## 8. Gravatar integration

### 8.1 Avatar resolution

Gravatar identifies users by a hash of their email address. The current specification uses **SHA-256** of the address after trimming whitespace and lower-casing it - MD5 is legacy and is not used here.

```python
def gravatar_url(email: str, size: int = 200, default: str = "mp") -> str:
    digest = hashlib.sha256(email.strip().lower().encode("utf-8")).hexdigest()
    query = urlencode({"s": size, "d": default, "r": "pg"})
    return f"https://gravatar.com/avatar/{digest}?{query}"
```

Resolution follows a deterministic fallback chain: an uploaded override, then the Gravatar image, then a generated initials avatar rendered locally. The `d` parameter handles the fallback server-side at Gravatar's CDN, so a missing avatar never produces a broken image.

### 8.2 Design decisions

- **The hash is computed server-side and returned as part of the employee representation.** The browser never needs the raw email to render an avatar, which keeps addresses out of any client-side caching or logging path.
- **Images are requested directly by the browser from Gravatar's CDN**, not proxied. Proxying would put an external dependency in the critical path of every API response and burn function execution time for no benefit.
- **The integration sits behind an `AvatarProvider` port.** The Gravatar implementation is one adapter; a fake is injected in tests so the suite makes no network calls, and an internal provider could be substituted without touching the service layer.
- **Requested size is capped and `r=pg` is enforced**, so the application never renders an unrated third-party image in a corporate context.
- **Failures are non-fatal.** Avatar rendering is presentation, never a reason for a request to fail.

### 8.3 Optional upload

The nice-to-have upload path stores images in object storage and records the resulting URL in `avatar_override_url`, which takes precedence over Gravatar. Uploads are validated by content sniffing rather than by file extension, re-encoded to strip EXIF metadata (which can carry GPS coordinates), capped at 2 MB, and served from a bucket that permits no execution.

### 8.4 Profile enrichment

Gravatar also exposes a public profile API. When an administrator enters an email on the create-employee form, the system looks it up and offers to prefill display name, job title and location, which the administrator can accept or ignore. It is a small feature that demonstrates the integration is understood as a data source rather than only an image URL.

---

## 9. Security and privacy

### 9.1 Authentication

Email and password, with **Argon2id** hashing (memory-hard, and the current OWASP recommendation over bcrypt for new systems). Short-lived JWT access tokens (15 minutes) with rotating refresh tokens. Tokens are signed with HS256 using a secret held in the platform's encrypted environment store and never committed.

### 9.2 Authorisation

Two roles, kept deliberately minimal:

| Role | Read employees | Read salary | Write | Import/export | Audit log |
|---|---|---|---|---|---|
| `viewer` | ✓ | ✗ | ✗ | Export only | ✗ |
| `hr_admin` | ✓ | ✓ | ✓ | ✓ | ✓ |

Authorisation is a route-level dependency, so an endpoint cannot be added without a policy decision being made explicitly.

### 9.3 Salary confidentiality

Salary is the one field in this dataset with genuine confidentiality weight, and it is handled as a **field-level authorisation** concern rather than a UI concern. The API selects a different response schema by role: for a `viewer` the salary key is **absent from the payload**, not null and not masked. Nothing that reaches an unauthorised client ever contains the value, so no amount of inspecting network traffic reveals it. Salary-based filters and sorts are likewise rejected for viewers, since either would allow the value to be inferred by binary search.

### 9.4 Input handling

- All request bodies are parsed and validated by Pydantic models at the boundary; unknown fields are rejected rather than ignored.
- All database access goes through SQLAlchemy with bound parameters. Identifiers that cannot be bound - sort columns - are resolved through an allow-list (§6.3).
- React escapes rendered content by default; `dangerouslySetInnerHTML` appears nowhere in the codebase.
- CORS is restricted to the deployed frontend origin.
- Rate limiting is applied to authentication endpoints to blunt credential stuffing.
- Security headers (HSTS, `X-Content-Type-Options`, a restrictive CSP allowing `gravatar.com` as an image source) are set at the platform edge.

### 9.5 POPIA alignment

The system processes personal information of South African data subjects and is designed with the Protection of Personal Information Act's conditions in mind:

| Condition | How it is addressed |
|---|---|
| Minimality | Only fields required by the brief are collected; no ID numbers, addresses or contact numbers |
| Purpose specification | Data is used solely for organisational structure management |
| Security safeguards | Encryption in transit, hashed credentials, role-based access, least-privilege database user |
| Accountability | Every change is attributable through the audit log |
| Data subject participation | Records are individually retrievable, correctable and erasable, including a hard-delete path for erasure requests |

This is a design-level alignment, not a compliance certification - a distinction the document states plainly rather than overclaiming.

### 9.6 Audit trail

Every create, update, delete, restore and reassignment writes an `audit_log` row containing the actor, the action, and before/after JSON snapshots, inside the same transaction as the change itself. Either both commit or neither does, so the audit log cannot disagree with the data. It is exposed as a per-employee timeline in the UI.

---

## 10. Deployment and operations

### 10.1 Topology

| Component | Platform | Rationale |
|---|---|---|
| React SPA | Vercel static hosting + CDN | Global edge caching, automatic HTTPS, atomic deploys |
| FastAPI API | Vercel Python function | Same platform and domain as the SPA, so no CORS preflight in production and one deployment pipeline |
| PostgreSQL | Neon (serverless Postgres) | Free tier persists indefinitely; database branching gives a real preview environment per pull request |
| Object storage | Vercel Blob or Supabase Storage | Only required if avatar upload is enabled |

Hosting alternatives were assessed against one criterion above all: **an assessor clicking the URL must get an immediate response.** Free container platforms that suspend idle services and cold-start in roughly a minute were rejected for that reason alone, regardless of their other merits. Serverless functions cold-start in well under a second and the database is always warm.

### 10.2 Environments

| Environment | Trigger | Database |
|---|---|---|
| Local | `docker compose up` | Postgres 16 container |
| Preview | Every pull request | Neon branch, seeded automatically |
| Production | Merge to `main` | Neon primary |

### 10.3 Serverless and database connections

A serverless runtime may hold many short-lived instances, and a classic per-process connection pool would exhaust PostgreSQL's connection limit. The application therefore connects through **Neon's pooled endpoint (PgBouncer)** and configures SQLAlchemy with `NullPool`, delegating pooling to the proxy. This also rules out session-level state such as prepared-statement caching and `SET` statements, which the code avoids deliberately. This is the single most common way a working local application fails in serverless production, and it is designed for rather than discovered.

### 10.4 Schema migrations

Alembic, with migrations committed to the repository and applied as a pipeline step before the new version receives traffic. Migrations are written to be backward-compatible with the previous application version, so a deployment can be rolled back without a data restore.

### 10.5 CI/CD

GitHub Actions on every push: Ruff lint and format check, `mypy`, `pytest` with coverage gating, `tsc --noEmit`, ESLint, Vite production build, and a Playwright smoke test against the preview deployment. A red pipeline blocks the merge; a green merge deploys automatically. Deployments are atomic and instantly revertible to any prior build.

### 10.6 Observability

Structured JSON logs with a correlation ID per request, propagated from the SPA so a user-reported problem can be traced end to end. `/health` reports API liveness and database reachability. Platform-level metrics cover invocation count, duration and error rate. Slow-query logging is enabled on the database.

Optional outbound webhooks emit `employee.created`, `employee.updated` and `employee.reassigned` events with an HMAC-SHA256 signature over the payload, giving downstream systems - an SAP HCM interface, for instance - an integration point that does not require polling.

---

## 11. Testing strategy

| Level | Tooling | Scope |
|---|---|---|
| Unit | pytest | Domain rules, deletion policies, Gravatar hashing, validators |
| Integration | pytest + testcontainers (real PostgreSQL) | Repositories, recursive CTEs, constraints, triggers |
| API contract | pytest + `httpx.AsyncClient` | Status codes, problem documents, RBAC, salary redaction |
| Concurrency | pytest with parallel sessions | Cycle prevention and optimistic-lock conflicts |
| Frontend unit | Vitest + Testing Library | Hooks, formatters, form validation |
| End-to-end | Playwright | Login, create, reassign by drag, filter, delete, export |

Integration tests run against real PostgreSQL rather than SQLite, because the behaviour under test - recursive CTEs, deferred constraint triggers, partial indexes, `NUMERIC` semantics - does not exist in SQLite. A test suite that passes against a database the application never uses tests the wrong thing.

The **cycle-prevention matrix** is treated as the flagship test: self-assignment, direct inversion (A↔B), indirect cycles at depths 2 through 5, reassignment to an unrelated branch (must succeed), reassignment to `NULL` (must succeed), and two concurrent inverse reassignments in separate transactions (exactly one must fail).

---

## 12. Design patterns applied

| Pattern | Where | Why here |
|---|---|---|
| Layered architecture | API structure | Keeps business rules independent of HTTP and of the ORM |
| Repository | `repositories/` | Query construction isolated from rules; services testable against fakes |
| Service layer | `services/` | Single place where invariants and transaction boundaries live |
| Unit of Work | Session-per-request dependency | Data change and its audit record commit atomically |
| Dependency Injection | FastAPI `Depends` | Auth, session and policies are composable and overridable in tests |
| DTO / schema mapping | Pydantic request and response models | Prevents internal fields leaking; enables role-specific response shapes |
| Adapter | `GravatarAdapter`, `StorageAdapter` | External services behind narrow ports, replaceable and fakeable |
| Strategy | `DeletionPolicy` | Three deletion behaviours without branching logic through the service |
| Optimistic offline lock | `version` column + `If-Match` | Concurrent edits without holding locks across user think-time |
| Specification (lightweight) | Composable list filters | Filter criteria combine without a combinatorial explosion of query methods |
| Composite | Chart node tree in the SPA | Uniform treatment of a node and its subtree |
| Container / presentational + custom hooks | React features | Data fetching separated from rendering |

Patterns are listed only where they are actually used and earn their place. A pattern applied for its own name is complexity without benefit, and the absence of, for instance, an event bus or a CQRS split is as deliberate as the presence of the entries above.

---

## 13. Technology decision register

| Decision | Chosen | Alternatives considered | Rationale | Accepted trade-off |
|---|---|---|---|---|
| Database | PostgreSQL 16 (Neon) | MySQL, Firestore, MongoDB, Neo4j | Recursive CTEs, deferred constraint triggers, partial indexes, exact `NUMERIC` for salary, transactional integrity for the acyclicity invariant | Relational schema changes need migrations |
| Hierarchy model | Adjacency list + recursive CTE | Materialised path, closure table, `ltree` | Single authoritative representation; O(1) writes; no derived state to drift | Deep reads cost a recursive query |
| API framework | FastAPI (Python 3.12) | Express/NestJS, Spring Boot, Django REST, ASP.NET Core | Pydantic validates at the boundary and generates OpenAPI from the same types, so the published contract cannot drift; async by default; fastest path to a documented, tested API | Python is slower per request than the JVM - irrelevant at this scale, where latency is dominated by network and database |
| Full-stack alternative | Rejected: Next.js | - | Next.js would give one build and one deployment, and it was a close second. It was rejected because it collapses the API into the UI's rendering model, and an independently documented, independently testable HTTP contract is a more valuable artefact for an organisation whose work is systems integration | Two build pipelines instead of one |
| Enterprise alternative | Rejected: Spring Boot + React | - | Aligns with JVM-heavy delivery environments and produces a literal compiled artefact, but adds substantial ceremony and configuration surface for no functional advantage on this domain, within a one-week window | Forgoes JVM ecosystem familiarity |
| Frontend | React 19 + TypeScript + Vite | Angular, Vue, Svelte | Strongest ecosystem for the two hard UI problems here - a virtualised interactive graph and a server-driven data table; end-to-end type safety from the generated client | Larger bundle than Svelte |
| Styling | Tailwind CSS + shadcn/ui | Material UI, Chakra, plain CSS | Accessible Radix primitives owned in-repo rather than imported, so components can be tailored without fighting a theme system | Verbose class strings |
| Chart rendering | React Flow + Dagre | D3 hierarchy, `react-organizational-chart`, GoJS | Pan, zoom, minimap and drag interaction out of the box; nodes stay ordinary React components; viewport virtualisation handles large organisations | Heavier than a static SVG tree |
| Server state | TanStack Query | Redux Toolkit Query, SWR, manual | Optimistic updates with automatic rollback, which is exactly what drag-to-reassign needs | Another concept to learn |
| ORM | SQLAlchemy 2.0 async | Tortoise, Prisma (Python), raw SQL | Mature, fully typed, and unusually good at dropping to raw SQL for the recursive CTEs without abandoning the ORM elsewhere | Steeper learning curve |
| Migrations | Alembic | Hand-written SQL | Autogeneration with reviewable, version-controlled output | Autogenerated migrations need review |
| Hosting | Vercel + Neon | Render, Railway, Fly.io, AWS, Heroku | Free tiers that suspend idle services cold-start in roughly a minute; an assessor must not wait. Serverless functions start in under a second and the database is always available | Serverless connection handling must be designed for (§10.3) |

---

## 14. Performance and scalability

| Concern | Approach |
|---|---|
| Hierarchy reads | Index on `manager_id`; recursive CTE resolves a 5 000-node subtree in single-digit milliseconds |
| Chart rendering | Lazy subtree loading and viewport virtualisation; the DOM holds only visible nodes |
| List view | Server-side pagination, filtering and sorting; keyset pagination available for deep pages |
| Search | GIN trigram index for fuzzy matching, rather than an unindexed leading-wildcard `LIKE` |
| Static delivery | Hashed, immutable assets served from CDN edge |
| Database connections | Externalised pooling (§10.3) |
| Scaling ceiling | Comfortable to roughly 100 000 employees. Beyond that, the migration is a closure table maintained as a derived read model |

---

## 15. Known limitations and roadmap

Stated plainly, because a design document that claims no limitations is not describing a real system.

1. **Position is free text.** Typos create distinct positions. A normalised job-catalogue entity is the correct fix.
2. **No effective dating.** The system stores the organisation as it is now, not as it was on a given date. Adding validity intervals to reporting assignments would allow historical org charts and planned future restructures - the model SAP HCM uses, and the most valuable single extension.
3. **Two roles only.** Real HR access control is usually scoped to organisational units, so a manager sees their own branch. That needs subtree-scoped authorisation.
4. **No multi-tenancy.** A single organisation is assumed.
5. **Single-parent hierarchy.** Matrix reporting (a solid-line and a dotted-line manager) would require a separate edge table and changes the tree to a DAG, with correspondingly harder cycle rules.
6. **Refresh tokens are not revocable before expiry** without a denylist store, which is acceptable at this scale but would not be in production.
7. **Audit log grows unbounded.** Partitioning by month and archiving would be needed at volume.

---

## Appendix A - Local setup

```bash
git clone «repository-url» && cd employee-hierarchy
cp .env.example .env            # DATABASE_URL, JWT_SECRET, CORS_ORIGINS
docker compose up --build       # API :8000, SPA :5173, Postgres :5432
docker compose exec api alembic upgrade head
docker compose exec api python -m app.seed --employees 250
```

Seeding writes to the configured database through the same service layer as the application; no data is mocked, hardcoded or read from local files at runtime.

## Appendix B - Configuration

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | Pooled PostgreSQL connection string |
| `JWT_SECRET` | Access and refresh token signing key |
| `JWT_ACCESS_TTL_SECONDS` | Access token lifetime (default 900) |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `GRAVATAR_DEFAULT_IMAGE` | Fallback avatar style (default `mp`) |
| `STORAGE_BUCKET_URL` | Object storage endpoint for avatar uploads |
| `WEBHOOK_SIGNING_SECRET` | HMAC key for outbound integration events |

## Appendix C - Glossary

| Term | Meaning |
|---|---|
| Adjacency list | Hierarchy stored as a self-referencing parent pointer on each row |
| Recursive CTE | SQL `WITH RECURSIVE` construct that walks a hierarchy in a single query |
| Deferred constraint trigger | A trigger evaluated at `COMMIT` rather than per statement |
| Optimistic lock | Conflict detection by version comparison at write time, without holding a lock |
| Rooted forest | A set of trees; here, an organisation with one or more managerless employees |
| Span of control | Number of direct reports a manager has |