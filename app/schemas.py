from typing import List, Optional
from pydantic import BaseModel


# ── CSV row after parsing ────────────────────────────────────────────────────

class HospitalRow(BaseModel):
    name: str
    address: str
    phone: Optional[str] = None


# ── Per-hospital result that ends up in the bulk response ───────────────────

class HospitalResult(BaseModel):
    row: int
    hospital_id: Optional[int] = None
    name: str
    status: str          # "created_and_activated" | "failed"
    error: Optional[str] = None


# ── Top-level response for POST /hospitals/bulk ──────────────────────────────

class BulkCreateResponse(BaseModel):
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    processing_time_seconds: float
    batch_activated: bool
    hospitals: List[HospitalResult]


# ── Response for GET /hospitals/bulk/{batch_id}/status ──────────────────────

class BatchStatusResponse(BaseModel):
    batch_id: str
    total_hospitals: int
    processed_hospitals: int
    failed_hospitals: int
    batch_activated: bool
    hospitals: List[HospitalResult]


# ── Response for POST /hospitals/bulk/validate ───────────────────────────────

class ValidationResponse(BaseModel):
    valid: bool
    total_rows: int
    errors: List[str]
