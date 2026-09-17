from __future__ import annotations

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.avatars import gravatar_url, resolve_avatar_url
from app.core.security import get_current_user
from app.core.uploads import read_capped
from app.db.session import get_db
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.repositories.employee_repository import EmployeeRepository
from app.schemas.profile import ProfileEmployee, ProfilePerson, ProfileResponse
from app.services.avatar_service import MAX_AVATAR_BYTES, AvatarService

router = APIRouter(prefix="/api/v1/profile", tags=["profile"])

_PROFILE_GRAVATAR_PX = 256


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


async def _build_profile(session: AsyncSession, user: AppUser) -> ProfileResponse:
    record = await EmployeeRepository(session).get_by_email(user.email)
    employee: ProfileEmployee | None = None
    if record is not None:
        related = (
            (
                await session.execute(
                    select(Employee)
                    .where(
                        Employee.deleted_at.is_(None),
                        or_(
                            Employee.id == record.manager_id,
                            Employee.manager_id == record.id,
                        ),
                    )
                    .order_by(Employee.last_name)
                )
            )
            .scalars()
            .all()
        )
        manager = next((e for e in related if e.id == record.manager_id), None)
        reports = [e for e in related if e.manager_id == record.id]
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
        can_view_salary=user.role == "hr_admin",
        can_edit=user.role == "hr_admin",
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
    user: AppUser = Depends(get_current_user),
) -> ProfileResponse:
    return await _build_profile(session, user)


@router.put("/avatar", response_model=ProfileResponse)
async def upload_profile_avatar(
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> ProfileResponse:
    raw = await read_capped(file, MAX_AVATAR_BYTES, what="Image")
    avatars = AvatarService(session)
    previous_url = user.avatar_override_url
    user.avatar_override_url = await avatars.store(raw)
    await avatars.discard_if_unused(previous_url)
    await session.commit()
    return await _build_profile(session, user)


@router.delete("/avatar", response_model=ProfileResponse)
async def remove_profile_avatar(
    session: AsyncSession = Depends(get_db),
    user: AppUser = Depends(get_current_user),
) -> ProfileResponse:
    previous_url = user.avatar_override_url
    user.avatar_override_url = None
    await AvatarService(session).discard_if_unused(previous_url)
    await session.commit()
    return await _build_profile(session, user)
