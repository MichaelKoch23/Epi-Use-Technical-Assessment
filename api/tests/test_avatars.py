from __future__ import annotations

import io

from PIL import Image
from sqlalchemy import text

from app.core.avatars import UPLOADED_AVATAR_PREFIX


def _png(width: int = 800, height: int = 400) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (0, 58, 107)).save(out, format="PNG")
    return out.getvalue()


def _files(content: bytes, name: str = "photo.png", content_type: str = "image/png"):
    return {"file": (name, content, content_type)}


async def test_admin_uploads_an_employee_photo_that_is_served_normalised(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")

    response = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": f'"{employee.version}"'},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["avatar_url"].startswith(UPLOADED_AVATAR_PREFIX)
    assert body["avatar_url"] == body["avatar_override_url"]
    assert body["version"] == employee.version + 1

    image = await api_client.get(body["avatar_url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/webp"
    assert "immutable" in image.headers["cache-control"]
    with Image.open(io.BytesIO(image.content)) as decoded:
        assert decoded.size == (512, 512)


async def test_photo_change_is_recorded_in_the_audit_trail(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")
    await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": f'"{employee.version}"'},
    )

    audit = await api_client.get(
        f"/api/v1/employees/{employee.id}/audit", headers=headers
    )

    latest = audit.json()["items"][0]
    assert latest["action"] == "employee.updated"
    assert latest["before"]["avatar_override_url"] is None
    assert latest["after"]["avatar_override_url"].startswith(UPLOADED_AVATAR_PREFIX)


async def test_replacing_a_photo_deletes_the_old_image(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")
    first = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": '"1"'},
    )
    old_url = first.json()["avatar_url"]

    second = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png(300, 300)),
        headers={**headers, "If-Match": '"2"'},
    )

    assert second.json()["avatar_url"] != old_url
    assert (await api_client.get(old_url)).status_code == 404


async def test_removing_a_photo_falls_back_to_gravatar(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")
    uploaded = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": '"1"'},
    )

    response = await api_client.delete(
        f"/api/v1/employees/{employee.id}/avatar",
        headers={**headers, "If-Match": '"2"'},
    )

    assert response.status_code == 200
    assert response.json()["avatar_url"].startswith("https://gravatar.com/avatar/")
    assert (await api_client.get(uploaded.json()["avatar_url"])).status_code == 404


async def test_stale_version_is_rejected_and_nothing_is_stored(
    api_client, auth_headers, employee_factory, db_session
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")

    response = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": '"99"'},
    )

    assert response.status_code == 409
    count = (
        await db_session.execute(text("SELECT count(*) FROM avatar_image"))
    ).scalar_one()
    assert count == 0


async def test_non_image_upload_is_rejected(api_client, auth_headers, employee_factory):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")

    response = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(b"<svg onload=alert(1)>", "x.svg", "image/svg+xml"),
        headers={**headers, "If-Match": '"1"'},
    )

    assert response.status_code == 422


async def test_viewer_cannot_change_an_employee_photo(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("viewer")

    response = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": '"1"'},
    )

    assert response.status_code == 403


async def test_uploaded_avatar_path_survives_a_patch_round_trip(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")
    uploaded = await api_client.put(
        f"/api/v1/employees/{employee.id}/avatar",
        files=_files(_png()),
        headers={**headers, "If-Match": '"1"'},
    )

    response = await api_client.patch(
        f"/api/v1/employees/{employee.id}",
        json={
            "position": "Architect",
            "avatar_override_url": uploaded.json()["avatar_url"],
        },
        headers={**headers, "If-Match": '"2"'},
    )

    assert response.status_code == 200, response.text


async def test_relative_avatar_urls_other_than_uploads_are_still_rejected(
    api_client, auth_headers, employee_factory
):
    employee = await employee_factory()
    headers = await auth_headers("hr_admin")

    response = await api_client.patch(
        f"/api/v1/employees/{employee.id}",
        json={"avatar_override_url": "/api/v1/avatars/../employees"},
        headers={**headers, "If-Match": '"1"'},
    )

    assert response.status_code == 422


async def test_profile_links_the_employee_record_sharing_the_account_email(
    api_client, user_factory, employee_factory
):
    manager = await employee_factory(first_name="Thandi", position="CTO")
    me = await employee_factory(
        first_name="Michael", email="Michael.Koch@example.com", manager_id=manager.id
    )
    await employee_factory(first_name="Report", manager_id=me.id)
    _, password = await user_factory(email="michael.koch@example.com", role="viewer")
    login = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "michael.koch@example.com", "password": password},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    response = await api_client.get("/api/v1/profile", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "viewer"
    assert body["has_uploaded_avatar"] is False
    assert body["avatar_url"].startswith("https://gravatar.com/avatar/")
    assert body["employee"]["id"] == str(me.id)
    assert body["employee"]["manager"]["first_name"] == "Thandi"
    assert [r["first_name"] for r in body["employee"]["direct_reports"]] == ["Report"]
    assert "salary" not in body["employee"]


async def test_any_user_can_set_and_remove_their_own_photo(api_client, auth_headers):
    headers = await auth_headers("viewer")

    uploaded = await api_client.put(
        "/api/v1/profile/avatar", files=_files(_png()), headers=headers
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["has_uploaded_avatar"] is True
    url = uploaded.json()["avatar_url"]
    me = await api_client.get("/api/v1/auth/me", headers=headers)
    assert me.json()["avatar_url"] == url

    removed = await api_client.delete("/api/v1/profile/avatar", headers=headers)
    assert removed.json()["has_uploaded_avatar"] is False
    assert removed.json()["employee"] is None
    assert (await api_client.get(url)).status_code == 404


async def test_unknown_avatar_is_a_404(api_client):
    response = await api_client.get(
        "/api/v1/avatars/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 404
