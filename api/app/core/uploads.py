"""Bounded reads of multipart uploads, shared by every route that takes a file."""

from __future__ import annotations

from fastapi import HTTPException, UploadFile

_CHUNK_BYTES = 64 * 1024


async def read_capped(file: UploadFile, limit: int, *, what: str) -> bytes:
    """Read the upload, refusing anything over `limit`.

    `await file.read()` with no argument buffers the entire body into
    memory before a single validation rule runs, so one request can
    exhaust the instance's memory regardless of how carefully the contents
    are checked afterwards. Reading in chunks lets the limit be enforced
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
                detail=f"{what} exceeds the {limit // (1024 * 1024)} MB limit",
            )
        chunks.append(chunk)
    return b"".join(chunks)
