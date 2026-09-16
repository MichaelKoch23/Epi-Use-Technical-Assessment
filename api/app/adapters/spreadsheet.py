"""Parses an uploaded import file into plain string-keyed rows. Both
formats collapse to the same shape - `list[dict[str, str]]`, header row
first - so `ImportService` never has to know which one it got (§ import
validation)."""

from __future__ import annotations

import csv
import io
import zipfile

import openpyxl

# A file that parses is not yet a file worth processing: these caps bound
# the work a single upload can provoke *after* the byte-size limit in the
# router has already been satisfied. A few hundred KB of XLSX can expand
# into millions of cells (the "zip bomb" shape), and a CSV field with no
# terminating quote can otherwise consume the whole file as one value.
MAX_ROWS = 50_000
MAX_FIELD_CHARS = 100_000


def parse_csv(content: bytes) -> list[dict[str, str]]:
    try:
        # Tolerate a BOM from Excel-exported CSVs.
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError(
            "File is not valid UTF-8 text - re-export it as UTF-8 CSV"
        ) from exc

    previous_limit = csv.field_size_limit(MAX_FIELD_CHARS)
    try:
        reader = csv.DictReader(io.StringIO(text))
        rows: list[dict[str, str]] = []
        for row in reader:
            if len(rows) >= MAX_ROWS:
                raise ValueError(f"File exceeds the {MAX_ROWS:,}-row limit")
            rows.append({k: (v or "").strip() for k, v in row.items() if k})
        return rows
    except csv.Error as exc:
        raise ValueError(f"Malformed CSV: {exc}") from exc
    finally:
        csv.field_size_limit(previous_limit)


def parse_xlsx(content: bytes) -> list[dict[str, str]]:
    try:
        workbook = openpyxl.load_workbook(
            io.BytesIO(content), read_only=True, data_only=True
        )
    except (zipfile.BadZipFile, KeyError, ValueError, TypeError) as exc:
        # openpyxl surfaces a corrupt or non-XLSX payload as any of these.
        raise ValueError(f"File is not a readable .xlsx workbook: {exc}") from exc

    if not workbook.worksheets:
        raise ValueError("Workbook contains no sheets")

    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows, ())]

    parsed: list[dict[str, str]] = []
    for raw_row in rows:
        if all(cell is None for cell in raw_row):
            continue
        if len(parsed) >= MAX_ROWS:
            raise ValueError(f"File exceeds the {MAX_ROWS:,}-row limit")
        record: dict[str, str] = {}
        for header, cell in zip(headers, raw_row, strict=False):
            if not header:
                continue
            record[header] = "" if cell is None else str(cell).strip()[:MAX_FIELD_CHARS]
        parsed.append(record)
    return parsed


def parse_upload(filename: str, content: bytes) -> list[dict[str, str]]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        return parse_xlsx(content)
    if lower.endswith(".csv"):
        return parse_csv(content)
    raise ValueError(f"Unsupported file type: {filename!r} (expected .csv or .xlsx)")
