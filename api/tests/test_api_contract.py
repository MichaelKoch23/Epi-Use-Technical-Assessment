from __future__ import annotations

from decimal import Decimal

import pytest

PROTECTED_ROUTES = [
    ("GET", "/api/v1/employees"),
    ("POST", "/api/v1/employees"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000"),
    ("PATCH", "/api/v1/employees/00000000-0000-0000-0000-000000000000"),
    ("DELETE", "/api/v1/employees/00000000-0000-0000-0000-000000000000"),
    ("POST", "/api/v1/employees/00000000-0000-0000-0000-000000000000/restore"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000/deletion-preview"),
    ("PUT", "/api/v1/employees/00000000-0000-0000-0000-000000000000/manager"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000/subtree"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000/reporting-line"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000/audit"),
    ("GET", "/api/v1/hierarchy/roots"),
    ("GET", "/api/v1/analytics/org-summary"),
    ("GET", "/api/v1/analytics/branch/00000000-0000-0000-0000-000000000000"),
    ("GET", "/api/v1/exports/employees.csv"),
    ("POST", "/api/v1/imports/employees"),
    ("GET", "/api/v1/search?q=a"),
    ("GET", "/api/v1/audit"),
    ("GET", "/api/v1/employees/positions"),
    ("GET", "/api/v1/employees/managers"),
    ("PUT", "/api/v1/employees/00000000-0000-0000-0000-000000000000/avatar"),
    ("DELETE", "/api/v1/employees/00000000-0000-0000-0000-000000000000/avatar"),
    ("GET", "/api/v1/profile"),
    ("PUT", "/api/v1/profile/avatar"),
    ("DELETE", "/api/v1/profile/avatar"),
]


@pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
async def test_every_route_rejects_an_anonymous_caller(api_client, method, path):
    response = await api_client.request(method, path)
    assert response.status_code in (401, 403), (
        f"{method} {path} answered an unauthenticated caller with "
        f"{response.status_code}"
    )


@pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
async def test_every_route_rejects_a_forged_token(api_client, method, path):
    headers = {"Authorization": "Bearer not.a.real.token"}
    response = await api_client.request(method, path, headers=headers)
    assert response.status_code in (401, 403)


WRITE_ROUTES = [
    ("POST", "/api/v1/employees"),
    ("PATCH", "/api/v1/employees/00000000-0000-0000-0000-000000000000"),
    ("DELETE", "/api/v1/employees/00000000-0000-0000-0000-000000000000"),
    ("POST", "/api/v1/employees/00000000-0000-0000-0000-000000000000/restore"),
    ("PUT", "/api/v1/employees/00000000-0000-0000-0000-000000000000/manager"),
    ("GET", "/api/v1/employees/00000000-0000-0000-0000-000000000000/deletion-preview"),
    ("POST", "/api/v1/imports/employees"),
    ("PUT", "/api/v1/employees/00000000-0000-0000-0000-000000000000/avatar"),
    ("DELETE", "/api/v1/employees/00000000-0000-0000-0000-000000000000/avatar"),
]


@pytest.mark.parametrize(("method", "path"), WRITE_ROUTES)
async def test_viewer_cannot_reach_a_write_route(
    api_client, auth_headers, method, path
):
    headers = await auth_headers("viewer")
    response = await api_client.request(method, path, headers=headers)
    assert response.status_code == 403, (
        f"{method} {path} let a viewer through with {response.status_code}"
    )


async def test_viewer_employee_payload_has_no_salary_key(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory(salary=Decimal(750000))
    headers = await auth_headers("viewer")

    response = await api_client.get(f"/api/v1/employees/{employee.id}", headers=headers)

    assert response.status_code == 200
    assert "salary" not in response.json()
    assert "750000" not in response.text


async def test_admin_employee_payload_has_the_salary(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory(salary=Decimal(750000))
    headers = await auth_headers("hr_admin")

    response = await api_client.get(f"/api/v1/employees/{employee.id}", headers=headers)

    assert response.status_code == 200
    assert Decimal(response.json()["salary"]) == Decimal(750000)


SALARY_INFERENCE_QUERIES = [
    "min_salary=500000",
    "max_salary=500000",
    "sort=salary",
    "sort=salary&order=desc",
]


@pytest.mark.parametrize("query", SALARY_INFERENCE_QUERIES)
@pytest.mark.parametrize("path", ["/api/v1/employees", "/api/v1/exports/employees.csv"])
async def test_viewer_cannot_filter_or_sort_by_salary(
    api_client, auth_headers, employee_factory, path, query
):
    await employee_factory(salary=Decimal(10_000), last_name="Low")
    await employee_factory(salary=Decimal(900_000), last_name="High")
    headers = await auth_headers("viewer")

    response = await api_client.get(f"{path}?{query}", headers=headers)

    assert response.status_code == 403, (
        f"{path}?{query} answered a viewer with {response.status_code}; "
        "salary is inferable by bisection"
    )
    assert "High" not in response.text


@pytest.mark.parametrize("query", SALARY_INFERENCE_QUERIES)
@pytest.mark.parametrize("path", ["/api/v1/employees", "/api/v1/exports/employees.csv"])
async def test_admin_may_filter_and_sort_by_salary(
    api_client, auth_headers, employee_factory, path, query
):
    await employee_factory(salary=Decimal(900_000))
    headers = await auth_headers("hr_admin")

    response = await api_client.get(f"{path}?{query}", headers=headers)

    assert response.status_code == 200


async def test_viewer_analytics_omits_the_cost_object(
    api_client, auth_headers, employee_factory
):
    await employee_factory(salary=Decimal(750000))
    headers = await auth_headers("viewer")

    response = await api_client.get("/api/v1/analytics/org-summary", headers=headers)

    assert response.status_code == 200
    assert "cost" not in response.json()
    assert "750000" not in response.text


async def test_viewer_audit_feed_hides_salary_values_but_not_the_change(
    api_client, auth_headers, employee_factory, db_session, actor_id
):
    from app.services.employee_service import EmployeeService

    employee = await employee_factory(salary=Decimal(100000))
    service = EmployeeService(db_session)
    await service.update(
        employee.id,
        expected_version=employee.version,
        actor_id=actor_id,
        salary=Decimal(777777),
    )
    await db_session.commit()

    headers = await auth_headers("viewer")
    response = await api_client.get("/api/v1/audit", headers=headers)

    assert response.status_code == 200
    assert "777777" not in response.text
    assert any(item["salary_changed"] for item in response.json()["items"])


async def test_security_headers_are_present(api_client):
    response = await api_client.get("/api/v1/employees")

    assert response.status_code in (401, 403)
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers["Referrer-Policy"] == "no-referrer"


async def test_csp_lets_the_png_export_read_gravatar(api_client):
    """The chart export inlines avatars with fetch, which connect-src governs.

    img-src alone is not enough: it lets an avatar be shown, not read, and the
    exporter rejects with a bare DOM Event when a picture cannot be inlined -
    so narrowing this back to 'self' breaks the export with no usable message.
    """
    response = await api_client.get("/api/v1/employees")
    csp = response.headers["Content-Security-Policy"]

    connect = next(d for d in csp.split("; ") if d.startswith("connect-src"))
    assert "https://gravatar.com" in connect
    assert "https:;" not in connect and not connect.endswith("https:")


async def test_docs_csp_allows_the_swagger_and_redoc_bundles(api_client):
    """Swagger UI and ReDoc load from a CDN, which script-src 'self' blocks.

    The block is silent: the page returns 200 and renders as a blank white
    screen, because the bundle that fills #swagger-ui never executes. The
    inline SwaggerUIBundle({...}) call needs 'unsafe-inline' on top of the
    origin, so both have to be present for the console to appear at all.
    """
    for path in ("/docs", "/redoc"):
        response = await api_client.get(path)

        assert response.status_code == 200
        csp = response.headers["Content-Security-Policy"]
        script = next(d for d in csp.split("; ") if d.startswith("script-src"))
        assert "https://cdn.jsdelivr.net" in script
        assert "'unsafe-inline'" in script


async def test_docs_csp_does_not_relax_the_application(api_client):
    """The CDN allowance is scoped to the doc pages and must stay there.

    The access token lives in the SPA's localStorage, so script-src 'self' on
    every other response is what keeps it unreachable - widening the shared
    header to fix the console would trade that away.
    """
    response = await api_client.get("/api/v1/employees")
    csp = response.headers["Content-Security-Policy"]

    script = next(d for d in csp.split("; ") if d.startswith("script-src"))
    assert script == "script-src 'self'"


async def test_unknown_api_path_is_404_not_the_spa_shell(api_client):
    response = await api_client.get("/api/v1/employeez")

    assert response.status_code == 404
    assert "<html" not in response.text.lower()


async def test_oversized_import_upload_is_rejected(api_client, auth_headers):
    headers = await auth_headers("hr_admin")
    oversized = b"employee_number,first_name\n" + b"x" * (6 * 1024 * 1024)

    response = await api_client.post(
        "/api/v1/imports/employees",
        headers=headers,
        files={"file": ("big.csv", oversized, "text/csv")},
    )

    assert response.status_code == 413


async def test_malformed_upload_is_422_not_500(api_client, auth_headers):
    headers = await auth_headers("hr_admin")

    response = await api_client.post(
        "/api/v1/imports/employees",
        headers=headers,
        files={"file": ("broken.xlsx", b"definitely not a workbook", "application/*")},
    )

    assert response.status_code == 422


async def test_invalid_employee_payload_is_422_not_500(api_client, auth_headers):
    headers = await auth_headers("hr_admin")

    response = await api_client.post(
        "/api/v1/employees",
        headers=headers,
        json={
            "employee_number": "E1",
            "first_name": "A",
            "last_name": "B",
            "email": "a@b.co",
            "birth_date": "2099-01-01",
            "position": "Eng",
            "salary": "1",
            "avatar_override_url": "javascript:alert(1)",
        },
    )

    assert response.status_code == 422
    fields = {".".join(str(p) for p in e["loc"]) for e in response.json()["detail"]}
    assert any("birth_date" in f for f in fields)
    assert any("avatar_override_url" in f for f in fields)


async def test_login_is_rate_limited(api_client, user_factory):
    await user_factory(email="target@example.com", role="viewer", password="right")

    statuses = [
        (
            await api_client.post(
                "/api/v1/auth/login",
                json={"email": "target@example.com", "password": "wrong"},
            )
        ).status_code
        for _ in range(8)
    ]

    assert 429 in statuses, f"login was never rate limited: {statuses}"
    assert statuses[0] == 401


async def test_login_does_not_leak_whether_an_account_exists(api_client, user_factory):
    await user_factory(email="real@example.com", role="viewer", password="right")

    known = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "real@example.com", "password": "wrong"},
    )
    unknown = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "wrong"},
    )

    assert known.status_code == unknown.status_code == 401
    assert known.json() == unknown.json()


async def test_refresh_token_is_not_accepted_as_an_access_token(
    api_client, user_factory
):
    await user_factory(email="rt@example.com", role="hr_admin", password="pw")
    login = await api_client.post(
        "/api/v1/auth/login", json={"email": "rt@example.com", "password": "pw"}
    )
    refresh_token = login.json()["refresh_token"]

    response = await api_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {refresh_token}"}
    )

    assert response.status_code == 401
