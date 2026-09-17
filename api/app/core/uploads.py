from __future__ import annotations

from fastapi import HTTPException, UploadFile

_CHUNK_BYTES = 64 * 1024


async def read_capped(file: UploadFile, limit: int, *, what: str) -> bytes:
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(_CHUNK_BYTES):
        total += len(chunk)
        if total > limit:
            raise HTTPException(
                status_code=413,
                detail=f"{what} exceeds the {limit // (1024 * 1024)} MB limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)
