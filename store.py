"""
store.py
--------
Simple in-memory store that tracks the state of every bulk batch.

Using a plain dict here is fine given the assignment says in-memory
storage is acceptable.  If this ever needed to survive restarts or
span multiple workers, swapping this out for Redis would be straightforward.
"""

from typing import Dict, Optional
from app.schemas import BulkCreateResponse


# batch_id → BulkCreateResponse snapshot
_batches: Dict[str, BulkCreateResponse] = {}


def save_batch(result: BulkCreateResponse) -> None:
    _batches[result.batch_id] = result


def get_batch(batch_id: str) -> Optional[BulkCreateResponse]:
    return _batches.get(batch_id)


def list_batches() -> list:
    return list(_batches.values())
