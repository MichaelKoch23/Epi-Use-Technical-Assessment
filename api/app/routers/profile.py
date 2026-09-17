"""`/api/v1/profile` - the signed-in account's own profile page: who they
are, how their avatar is resolved, and the employee record that shares
their email, if any.

Kept outside `/auth/*` on purpose: the SPA's API client never retries
auth-path requests after refreshing an expired token (so a failed refresh
can't recurse), and an avatar upload should get that retry like any other
call.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.avatars import gravatar_url, resolve_avatar_url
from app.core.security import Principal, get_current_principal
from app.core.uploads import read_capped
from app.db.session import get_db
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.profile import ProfileEmployee, ProfilePerson, ProfileResponse
from app.services.avatar_service import MAX_AVATAR_BYTES, AvatarService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

# Large enough for the profile page's hero avatar on a high-DPI screen.
_PROFILE_GRAVATAR_PX = 256


async def _current_user(session: AsyncSession, principal: Principal) -> AppUser:
    user = (
        await session.execute(select(AppUser).where(AppUser.id == principal.id))
    ).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="Unknown user")
    return user


def _person(employee: Employee) -> ProfilePerson:
    return ProfilePerson(
        id=employee.id,
        first_name=employee.first_name,
        last_name=employee.last_name,
        position=employee.position,
        avatar_url=resolve_avatar_url(
            avatar_override_url=employee.avatar_override_url, email=employee.email
        ),
    )


async def _build_profile(
    session: AsyncSession, user: AppUser, principal: Principal
) -> ProfileResponse:
    repo = EmployeeRepository(session)
    record = await repo.get_by_email(user.email)
    employee: ProfileEmployee | None = None
    if record is not None:
        manager = await repo.get(record.manager_id) if record.manager_id else None
        reports = await repo.get_direct_reports(record.id)
        employee = ProfileEmployee(
            **_person(record).model_dump(),
            employee_number=record.employee_number,
            email=record.email,
            joined_at=record.created_at,
            manager=_person(manager) if manager else None,
            direct_reports=[
                _person(r) for r in sorted(reports, key=lambda r: r.last_name)
            ],
        )

    return ProfileResponse(
        id=user.id,
        email=user.email,
        role=user.role,
        can_view_salary=principal.is_admin,
        can_edit=principal.is_admin,
        avatar_url=resolve_avatar_url(
            avatar_override_url=user.avatar_override_url, email=user.email
        ),
        gravatar_url=gravatar_url(user.email, _PROFILE_GRAVATAR_PX),
        has_uploaded_avatar=user.avatar_override_url is not None,
        employee=employee,
    )


@router.get("", response_model=ProfileResponse)
async def get_profile(
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ProfileResponse:
    user = await _current_user(session, principal)
    return await _build_profile(session, user, principal)


@router.put("/avatar", response_model=ProfileResponse)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ProfileResponse:
    """Any signed-in user may set their *own* photo - it is not employee
    data, so it isn't gated on `hr_admin` like the employee equivalent."""
    user = await _current_user(session, principal)
    raw = await read_capped(file, MAX_AVATAR_BYTES, what="Image")
    avatars = AvatarService(session)
    previous_url = user.avatar_override_url
    user.avatar_override_url = await avatars.store(raw)
    await avatars.discard_if_unused(previous_url)
    await session.commit()
    return await _build_profile(session, user, principal)


@router.delete("/avatar", response_model=ProfileResponse)
async def remove_profile_avatar(
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(get_current_principal),
) -> ProfileResponse:
    user = await _current_user(session, principal)
    previous_url = user.avatar_override_url
    user.avatar_override_url = None
    await AvatarService(session).discard_if_unused(previous_url)
    await session.commit()
    return await _build_profile(session, user, principal)
