"""`POST /api/v1/imports/employees` - bulk CSV/XLSX import with a
`?dry_run=true` validation-only mode (§ import)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.adapters.spreadsheet import parse_upload
from app.core.config import settings
from app.core.security import Principal, require_role
from app.db.session import get_db
from app.schemas.import_ import ImportResult
from app.services.import_service import ImportService

router = APIRouter(prefix="/api/v1/imports", tags=["imports"])

_CHUNK_BYTES = 64 * 1024


async def _read_capped(file: UploadFile, limit: int) -> bytes:
    """Read the upload, refusing anything over `limit`.

    `await file.read()` with no argument buffers the entire body into
    memory before a single validation rule runs, so one request can
    exhaust the instance's memory regardless of how carefully the rows are
    checked afterwards. Reading in chunks lets the limit be enforced
    against what has actually arrived, and `Content-Length` is not trusted
    to do it - a chunked request does not have to send one, and a
    dishonest one can understate it.
    """
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"Import file exceeds the {limit // (1024 * 1024)} MB limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/employees", response_model=ImportResult)
async def import_employees(
    file: UploadFile = File(...),
    dry_run: bool = Query(False),
    session: AsyncSession = Depends(get_db),
    principal: Principal = Depends(require_role("hr_admin")),
) -> ImportResult:
    content = await _read_capped(file, settings.MAX_UPLOAD_BYTES)
    try:
        raw_rows = parse_upload(file.filename or "", content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    service = ImportService(session)
    plan = await service.validate(raw_rows)

    if dry_run:
        return plan.to_result(committed=False)

    # `commit` only actually writes when nothing in the plan is blocked -
    # a partial import is worse than none (§ import). The router commits
    # the transaction exactly once, for the whole file.
    result = await service.commit(plan, actor_id=principal.id)
    if result.committed:
        await session.commit()
    return result
