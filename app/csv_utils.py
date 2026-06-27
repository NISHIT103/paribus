import csv
import io
from typing import List, Tuple

from app.config import MAX_CSV_ROWS
from app.schemas import HospitalRow

REQUIRED_COLUMNS = {"name", "address"}
OPTIONAL_COLUMNS = {"phone"}
ALL_COLUMNS = REQUIRED_COLUMNS | OPTIONAL_COLUMNS


def parse_csv(content: bytes) -> Tuple[List[HospitalRow], List[str]]:
    """
    Parse raw CSV bytes into a list of HospitalRow objects.

    Returns a tuple of (rows, errors).  If errors is non-empty the caller
    should reject the upload rather than trying to process it.
    """
    errors: List[str] = []
    rows: List[HospitalRow] = []

    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        errors.append("File is not valid UTF-8.  Please save your CSV as UTF-8 and try again.")
        return rows, errors

    reader = csv.DictReader(io.StringIO(text))

    if reader.fieldnames is None:
        errors.append("CSV appears to be empty.")
        return rows, errors

    # Normalise header names so "Name " and "NAME" both work
    normalised_headers = {h.strip().lower() for h in reader.fieldnames}
    missing = REQUIRED_COLUMNS - normalised_headers
    if missing:
        errors.append(f"CSV is missing required column(s): {', '.join(sorted(missing))}.")
        return rows, errors

    for i, raw_row in enumerate(reader, start=1):
        # Re-key using stripped, lower-cased column names
        row = {k.strip().lower(): (v.strip() if v else "") for k, v in raw_row.items()}

        row_errors = _validate_row(i, row)
        if row_errors:
            errors.extend(row_errors)
            continue

        rows.append(
            HospitalRow(
                name=row["name"],
                address=row["address"],
                phone=row.get("phone") or None,
            )
        )

    if len(rows) > MAX_CSV_ROWS:
        errors.append(
            f"CSV contains {len(rows)} data rows but the maximum allowed is {MAX_CSV_ROWS}."
        )
        rows = []

    return rows, errors


def _validate_row(row_number: int, row: dict) -> List[str]:
    problems = []

    if not row.get("name"):
        problems.append(f"Row {row_number}: 'name' is required and cannot be blank.")

    if not row.get("address"):
        problems.append(f"Row {row_number}: 'address' is required and cannot be blank.")

    return problems
