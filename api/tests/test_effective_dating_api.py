from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from tests.conftest import EmployeeFactory

TODAY = datetime.now(UTC).date()
API = "/api/v1"


async def _org(employee_factory: EmployeeFactory, db_session: AsyncSession):
    root = await employee_factory()
    a = await employee_factory(manager_id=root.id)
    b = await employee_factory(manager_id=root.id)
    mover = await employee_factory(manager_id=a.id)
    await employee_factory(manager_id=mover.id)
    await db_session.commit()
    return root, a, b, mover


async def test_tree_and_roots_echo_the_resolved_date(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")

    roots = await api_client.get(f"{API}/hierarchy/roots", headers=headers)
    assert roots.status_code == 200, roots.text
    assert roots.json()["as_of"] == TODAY.isoformat()

    past = (TODAY - timedelta(days=5)).isoformat()
    tree = await api_client.get(
        f"{API}/hierarchy/tree", params={"as_of": past}, headers=headers
    )
    assert tree.status_code == 200, tree.text
    assert tree.json()["as_of"] == past
    assert len(tree.json()["items"]) == 5
    assert {item["depth"] for item in tree.json()["items"]} == {0}

    today_tree = await api_client.get(f"{API}/hierarchy/tree", headers=headers)
    assert max(item["depth"] for item in today_tree.json()["items"]) == 3


async def test_subtree_and_reporting_line_accept_as_of(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, _b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")

    subtree = await api_client.get(
        f"{API}/employees/{mover.id}/subtree",
        params={"as_of": TODAY.isoformat()},
        headers=headers,
    )
    assert subtree.status_code == 200, subtree.text
    assert subtree.json()["as_of"] == TODAY.isoformat()
    assert len(subtree.json()["items"]) == 2

    line = await api_client.get(
        f"{API}/employees/{mover.id}/reporting-line", headers=headers
    )
    assert line.status_code == 200
    assert line.json()["as_of"] == TODAY.isoformat()
    assert len(line.json()["items"]) == 2


async def test_a_historical_view_rooted_on_someone_since_deleted_still_reads(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    """The chart loads roots, then each root's subtree. Deleting the only root
    leaves yesterday's chart rooted on somebody who is gone today, so an
    existence check asking "is this person here now" fails the whole view
    rather than the one node. It has to ask about the date being read."""
    root, a, _b, _mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")
    yesterday = (TODAY - timedelta(days=1)).isoformat()

    # Backdate the opening runs so yesterday has a structure to read at all.
    await db_session.execute(
        text("UPDATE employee_assignment SET valid_from = :from_date"),
        {"from_date": TODAY - timedelta(days=30)},
    )
    await db_session.commit()

    deleted = await api_client.delete(
        f"{API}/employees/{root.id}",
        params={"policy": "promote_to_root"},
        headers=headers,
    )
    assert deleted.status_code in (200, 204), deleted.text

    roots = await api_client.get(
        f"{API}/hierarchy/roots", params={"as_of": yesterday}, headers=headers
    )
    assert roots.status_code == 200, roots.text
    assert [item["id"] for item in roots.json()["items"]] == [str(root.id)]

    subtree = await api_client.get(
        f"{API}/employees/{root.id}/subtree",
        params={"as_of": yesterday},
        headers=headers,
    )
    assert subtree.status_code == 200, subtree.text
    assert len(subtree.json()["items"]) == 5

    line = await api_client.get(
        f"{API}/employees/{a.id}/reporting-line",
        params={"as_of": yesterday},
        headers=headers,
    )
    assert line.status_code == 200, line.text
    assert [item["employee"]["id"] for item in line.json()["items"]] == [str(root.id)]

    # ...and today they really are gone.
    today_subtree = await api_client.get(
        f"{API}/employees/{root.id}/subtree",
        params={"as_of": TODAY.isoformat()},
        headers=headers,
    )
    assert today_subtree.status_code == 404, today_subtree.text


async def test_scheduling_a_move_then_cancelling_it(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")
    effective = (TODAY + timedelta(days=30)).isoformat()

    put = await api_client.put(
        f"{API}/employees/{mover.id}/manager",
        headers={**headers, "If-Match": f'"{mover.version}"'},
        json={
            "manager_id": str(b.id),
            "effective_from": effective,
            "reason": "Planned transfer",
        },
    )
    assert put.status_code == 200, put.text
    body = put.json()
    assert body["in_force_now"] is False
    assert body["effective_from"] == effective
    assert body["reason"] == "Planned transfer"
    assert body["employee"]["manager_id"] != str(b.id)

    listing = await api_client.get(f"{API}/hierarchy/scheduled", headers=headers)
    assert listing.status_code == 200
    scheduled = listing.json()["items"]
    assert len(scheduled) == 1
    assert scheduled[0]["employee_name"]
    assert scheduled[0]["effective_from"] == effective

    delete = await api_client.delete(
        f"{API}/hierarchy/scheduled/{scheduled[0]['id']}", headers=headers
    )
    assert delete.status_code == 204, delete.text

    after = await api_client.get(f"{API}/hierarchy/scheduled", headers=headers)
    assert after.json()["items"] == []


async def test_cancelling_an_in_force_assignment_is_refused(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, _b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")

    history = await api_client.get(
        f"{API}/employees/{mover.id}/assignment-history", headers=headers
    )
    current = history.json()["items"][0]
    assert current["in_force"] is True

    refused = await api_client.delete(
        f"{API}/hierarchy/scheduled/{current['id']}", headers=headers
    )
    assert refused.status_code == 422, refused.text
    assert refused.json()["type"].endswith("/scheduled-assignment-superseded")


async def test_effective_date_before_the_first_assignment_is_refused(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")

    response = await api_client.put(
        f"{API}/employees/{mover.id}/manager",
        headers={**headers, "If-Match": f'"{mover.version}"'},
        json={"manager_id": str(b.id), "effective_from": "2019-01-01"},
    )
    assert response.status_code == 422, response.text
    assert response.json()["type"].endswith("/effective-date-before-first-assignment")
    assert response.json()["errors"][0]["field"] == "effective_from"


async def test_reassign_still_honours_if_match(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")

    stale = await api_client.put(
        f"{API}/employees/{mover.id}/manager",
        headers={**headers, "If-Match": '"999"'},
        json={"manager_id": str(b.id)},
    )
    assert stale.status_code == 409, stale.text
    assert stale.json()["type"].endswith("/version-conflict")


async def test_move_preview_hides_cost_from_a_viewer(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, b, mover = await _org(employee_factory, db_session)

    admin = await api_client.post(
        f"{API}/employees/{mover.id}/move-preview",
        headers=await auth_headers("hr_admin"),
        json={"new_manager_id": str(b.id)},
    )
    assert admin.status_code == 200, admin.text
    body = admin.json()
    assert body["headcount"] == 2
    assert body["blocked"] is False
    assert body["depth_change"] == 0
    assert "cost_delta" in body
    assert isinstance(body["cost_delta"]["leaving"], str)
    assert isinstance(body["cost_delta"]["arriving"], str)

    viewer = await api_client.post(
        f"{API}/employees/{mover.id}/move-preview",
        headers=await auth_headers("viewer"),
        json={"new_manager_id": str(b.id)},
    )
    assert viewer.status_code == 200, viewer.text
    assert "cost_delta" not in viewer.json()


async def test_move_preview_reports_a_cyclic_move_as_blocked(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, a, _b, mover = await _org(employee_factory, db_session)

    response = await api_client.post(
        f"{API}/employees/{a.id}/move-preview",
        headers=await auth_headers("hr_admin"),
        json={"new_manager_id": str(mover.id)},
    )
    body = response.json()
    assert body["blocked"] is True
    assert body["blocked_chain"][0] == str(mover.id)
    assert body["blocked_chain_names"][0]
    assert body["blocked_at"] == TODAY.isoformat()


async def test_diff_hides_cost_from_a_viewer(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, _b, _mover = await _org(employee_factory, db_session)
    params = {"from": (TODAY - timedelta(days=30)).isoformat(), "to": TODAY.isoformat()}

    admin = await api_client.get(
        f"{API}/hierarchy/diff", params=params, headers=await auth_headers("hr_admin")
    )
    assert admin.status_code == 200, admin.text
    assert "cost" in admin.json()
    assert isinstance(admin.json()["cost"]["total_moved"], str)

    viewer = await api_client.get(
        f"{API}/hierarchy/diff", params=params, headers=await auth_headers("viewer")
    )
    assert viewer.status_code == 200
    assert "cost" not in viewer.json()


async def test_a_viewer_cannot_cancel_a_scheduled_assignment(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, _a, _b, mover = await _org(employee_factory, db_session)
    admin_headers = await auth_headers("hr_admin")

    history = await api_client.get(
        f"{API}/employees/{mover.id}/assignment-history", headers=admin_headers
    )
    assignment_id = history.json()["items"][0]["id"]

    response = await api_client.delete(
        f"{API}/hierarchy/scheduled/{assignment_id}",
        headers=await auth_headers("viewer"),
    )
    assert response.status_code == 403, response.text


async def test_assignment_history_is_newest_first_with_manager_names(
    api_client: AsyncClient, auth_headers, db_session, employee_factory
) -> None:
    _root, a, b, mover = await _org(employee_factory, db_session)
    headers = await auth_headers("hr_admin")
    effective = (TODAY + timedelta(days=10)).isoformat()

    await api_client.put(
        f"{API}/employees/{mover.id}/manager",
        headers={**headers, "If-Match": f'"{mover.version}"'},
        json={"manager_id": str(b.id), "effective_from": effective},
    )

    history = await api_client.get(
        f"{API}/employees/{mover.id}/assignment-history", headers=headers
    )
    items = history.json()["items"]
    assert [item["valid_from"] for item in items] == [effective, TODAY.isoformat()]
    assert items[0]["scheduled"] is True
    assert items[0]["manager_name"] == f"{b.first_name} {b.last_name}"
    assert items[1]["in_force"] is True
    assert items[1]["manager_name"] == f"{a.first_name} {a.last_name}"


async def test_unknown_assignment_is_a_404(
    api_client: AsyncClient, auth_headers
) -> None:
    response = await api_client.delete(
        f"{API}/hierarchy/scheduled/{uuid.uuid4()}",
        headers=await auth_headers("hr_admin"),
    )
    assert response.status_code == 404, response.text
    assert response.json()["type"].endswith("/assignment-not-found")
