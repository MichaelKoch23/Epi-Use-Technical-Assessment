from __future__ import annotations

from typing import Any

_MANAGERS = "/api/v1/employees/managers"


async def _create(api_client, headers, number, first, last, position, manager=None):
    body: dict[str, Any] = {
        "employee_number": number,
        "first_name": first,
        "last_name": last,
        "email": f"{number.lower()}@example.com",
        "birth_date": "1990-01-01",
        "position": position,
        "salary": "500000",
        "manager_id": manager,
    }
    response = await api_client.post("/api/v1/employees", headers=headers, json=body)
    assert response.status_code == 201, response.text
    return response.json()["id"]


async def _names(api_client, headers, query: str = "") -> list[str]:
    response = await api_client.get(f"{_MANAGERS}{query}", headers=headers)
    assert response.status_code == 200, response.text
    return [f"{row['first_name']} {row['last_name']}" for row in response.json()]


async def _org(api_client, headers) -> dict[str, str]:
    sales = await _create(
        api_client, headers, "E-S", "Riaan", "Mthembu", "Sales Director"
    )
    ops = await _create(api_client, headers, "E-O", "Zanele", "Smith", "Ops Director")
    eng = await _create(
        api_client, headers, "E-E", "Unrelated", "Manager", "Eng Manager"
    )
    await _create(
        api_client, headers, "E-1", "Thabo", "Davies", "Account Executive", sales
    )
    await _create(
        api_client, headers, "E-2", "Emma", "Molefe", "Account Executive", ops
    )
    await _create(
        api_client, headers, "E-3", "Ravi", "Naicker", "Software Engineer", eng
    )
    return {"sales": sales, "ops": ops, "eng": eng}


async def test_managers_are_scoped_to_the_current_filters(api_client, auth_headers):
    """The whole point: filter to a position, get that position's managers.

    Without this the picker opens on the first few names in the company, which
    are almost never the ones you are about to choose between.
    """
    headers = await auth_headers("hr_admin")
    await _org(api_client, headers)

    assert await _names(api_client, headers, "?position=Account+Executive") == [
        "Riaan Mthembu",
        "Zanele Smith",
    ]
    assert await _names(api_client, headers, "?position=Software+Engineer") == [
        "Unrelated Manager"
    ]


async def test_unfiltered_returns_every_manager(api_client, auth_headers):
    headers = await auth_headers("hr_admin")
    await _org(api_client, headers)

    assert sorted(await _names(api_client, headers)) == [
        "Riaan Mthembu",
        "Unrelated Manager",
        "Zanele Smith",
    ]


async def test_a_position_nobody_reports_to_returns_nothing(api_client, auth_headers):
    headers = await auth_headers("hr_admin")
    await _org(api_client, headers)

    assert await _names(api_client, headers, "?position=Sales+Director") == []


async def test_the_existing_manager_filter_does_not_narrow_the_choices(
    api_client, auth_headers
):
    """Otherwise the only option offered is the one already selected."""
    headers = await auth_headers("hr_admin")
    ids = await _org(api_client, headers)

    with_choice = await _names(
        api_client, headers, f"?position=Account+Executive&manager_id={ids['sales']}"
    )
    assert with_choice == ["Riaan Mthembu", "Zanele Smith"]


async def test_a_viewer_may_list_managers_but_not_filter_them_by_salary(
    api_client, auth_headers
):
    admin = await auth_headers("hr_admin")
    await _org(api_client, admin)
    viewer = await auth_headers("viewer")

    assert await _names(api_client, viewer, "?position=Account+Executive") == [
        "Riaan Mthembu",
        "Zanele Smith",
    ]

    refused = await api_client.get(f"{_MANAGERS}?min_salary=100000", headers=viewer)
    assert refused.status_code == 403, refused.text


async def test_managers_needs_authentication(api_client):
    # Matching the contract suite: the bearer scheme may answer either.
    assert (await api_client.get(_MANAGERS)).status_code in (401, 403)
