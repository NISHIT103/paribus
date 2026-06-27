"""
routers/hospitals.py
--------------------
HTTP layer for the bulk processing API.

Keeps routing thin: validate input, hand off to processor/store,
return the result.  No business logic lives here.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app import processor, store
from app.csv_utils import parse_csv
from app.schemas import BatchStatusResponse, ValidationResponse

router = APIRouter(prefix="/hospitals", tags=["hospitals"])

_ALLOWED_CONTENT_TYPES = {
    "text/csv",
    "application/csv",
    "application/vnd.ms-excel",
    "text/plain",           # some OS / clients send CSV as plain text
}


def _assert_csv(file: UploadFile) -> None:
    """Raise 400 if the uploaded file doesn't look like a CSV."""
    ct = (file.content_type or "").split(";")[0].strip().lower()
    if ct and ct not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Expected a CSV file, got content-type '{file.content_type}'.",
        )


# ── POST /hospitals/bulk ─────────────────────────────────────────────────────

@router.post("/bulk", response_model=None, status_code=200)
async def bulk_create(file: UploadFile = File(...)):
    """
    Upload a CSV file and bulk-create all hospitals in it.

    The CSV must have columns: name, address, phone (phone optional).
    Maximum 20 rows per upload.
    """
    _assert_csv(file)

    content = await file.read()
    if not content.strip():
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    hospitals, errors = parse_csv(content)
    if errors:
        raise HTTPException(status_code=422, detail={"csv_errors": errors})

    if not hospitals:
        raise HTTPException(status_code=400, detail="No valid hospital rows found in the CSV.")

    result = await processor.process_bulk(hospitals)
    return result


# ── POST /hospitals/bulk/validate ────────────────────────────────────────────

@router.post("/bulk/validate", response_model=ValidationResponse)
async def validate_csv(file: UploadFile = File(...)):
    """
    Dry-run: validate a CSV file without creating any hospitals.
    Returns a list of errors (if any) so the user can fix them first.
    """
    _assert_csv(file)

    content = await file.read()
    if not content.strip():
        return ValidationResponse(valid=False, total_rows=0, errors=["The uploaded file is empty."])

    rows, errors = parse_csv(content)
    return ValidationResponse(
        valid=len(errors) == 0,
        total_rows=len(rows),
        errors=errors,
    )


# ── GET /hospitals/bulk/{batch_id}/status ────────────────────────────────────

@router.get("/bulk/{batch_id}/status", response_model=BatchStatusResponse)
def batch_status(batch_id: str):
    """
    Look up the stored result for a previously submitted batch.
    Useful for checking whether a long-running upload finished successfully.
    """
    result = store.get_batch(batch_id)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"No batch found with id '{batch_id}'. "
                   "Batch results are stored in memory and will be lost on restart.",
        )
    return result


# ── GET /hospitals/bulk ──────────────────────────────────────────────────────

@router.get("/bulk")
def list_batches():
    """List all batches processed since the server started."""
    batches = store.list_batches()
    return {
        "total_batches": len(batches),
        "batches": [
            {
                "batch_id": b.batch_id,
                "total_hospitals": b.total_hospitals,
                "processed_hospitals": b.processed_hospitals,
                "failed_hospitals": b.failed_hospitals,
                "batch_activated": b.batch_activated,
                "processing_time_seconds": b.processing_time_seconds,
            }
            for b in batches
        ],
    }
