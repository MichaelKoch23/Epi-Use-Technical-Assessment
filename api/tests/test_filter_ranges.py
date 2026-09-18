from __future__ import annotations

import pytest

_LIST = "/api/v1/employees"
_EXPORT = "/api/v1/exports/employees.csv"


@pytest.mark.parametrize(
    ("label", "query"),
    [
        ("salary", "min_salary=200000&max_salary=40000"),
        ("birth date", "min_birth_date=2000-01-01&max_birth_date=1990-01-01"),
    ],
)
async def test_inverted_range_is_refused_rather_than_returning_nothing(
    api_client, auth_headers, label: str, query: str
) -> None:
    """An impossible range is a malformed question, not an empty answer.

    Answering it with a 200 and no rows says "nobody matches", which sends the
    reader looking at their data instead of at the bounds they typed.
    """
    headers = await auth_headers("hr_admin")
    response = await api_client.get(f"{_LIST}?{query}", headers=headers)

    assert response.status_code == 422, response.text
    assert "must not be greater than" in response.json()["detail"]


@pytest.mark.parametrize(
    "query",
    [
        "min_salary=40000&max_salary=200000",
        "min_salary=50000&max_salary=50000",
        "min_salary=200000",
        "max_salary=40000",
        "min_birth_date=1990-01-01&max_birth_date=2000-01-01",
        "min_birth_date=1990-01-01",
        "max_birth_date=2000-01-01",
    ],
)
async def test_valid_and_one_sided_ranges_are_accepted(
    api_client, auth_headers, query: str
) -> None:
    headers = await auth_headers("hr_admin")
    response = await api_client.get(f"{_LIST}?{query}", headers=headers)
    assert response.status_code == 200, response.text


async def test_the_export_refuses_an_inverted_range_too(
    api_client, auth_headers
) -> None:
    """The export shares employee_filter_params, so it must not be a way around it."""
    headers = await auth_headers("hr_admin")
    response = await api_client.get(
        f"{_EXPORT}?min_salary=200000&max_salary=40000", headers=headers
    )
    assert response.status_code == 422, response.text
