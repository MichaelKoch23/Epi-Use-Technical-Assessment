"""Parses an uploaded import file into plain string-keyed rows. Both
formats collapse to the same shape — `list[dict[str, str]]`, header row
first — so `ImportService` never has to know which one it got (§ import
validation)."""

from __future__ import annotations

import csv
import io

import openpyxl


def parse_csv(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig")  # tolerate a BOM from Excel-exported CSVs
    reader = csv.DictReader(io.StringIO(text))
    return [{k: (v or "").strip() for k, v in row.items() if k} for row in reader]


def parse_xlsx(content: bytes) -> list[dict[str, str]]:
    workbook = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    sheet = workbook.worksheets[0]
    rows = sheet.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows, ())]

    parsed: list[dict[str, str]] = []
    for raw_row in rows:
        if all(cell is None for cell in raw_row):
            continue
        record: dict[str, str] = {}
        for header, cell in zip(headers, raw_row, strict=False):
            if not header:
                continue
            record[header] = "" if cell is None else str(cell).strip()
        parsed.append(record)
    return parsed


def parse_upload(filename: str, content: bytes) -> list[dict[str, str]]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        return parse_xlsx(content)
    if lower.endswith(".csv"):
        return parse_csv(content)
    raise ValueError(f"Unsupported file type: {filename!r} (expected .csv or .xlsx)")
