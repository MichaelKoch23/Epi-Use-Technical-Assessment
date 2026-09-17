from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.spreadsheet import parse_upload
from app.core.config import settings
from app.core.security import Principal, require_role
from app.core.uploads import read_capped
from app.db.session import get_db
from app.schemas.import_ import ImportResult
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/employees", response_model=ImportResult)
async def import_employees(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> ImportResult:
    content = await read_capped(file, settings.MAX_UPLOAD_BYTES, what="Import file")
    try:
        raw_rows = parse_upload(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    service = ImportService(session)
    plan = await service.validate(raw_rows)

    if dry_run:
        return plan.to_result(committed=False)

    result = await service.commit(plan, actor_id=principal.id)
    if result.committed:
        await session.commit()
    return result
