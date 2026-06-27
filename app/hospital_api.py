"""
hospital_api.py
---------------
Async wrapper around the Hospital Directory API.

All network calls live here so the rest of the code doesn't have to think
about HTTP details.
"""

import httpx

from app.config import HOSPITAL_API_BASE, REQUEST_TIMEOUT
from app.schemas import HospitalRow


async def create_hospital(client: httpx.AsyncClient, hospital: HospitalRow, batch_id: str) -> dict:
    """
    POST /hospitals/

    Returns the created hospital dict on success, raises httpx.HTTPStatusError
    or httpx.RequestError on failure (callers should catch both).
    """
    payload = {
        "name": hospital.name,
        "address": hospital.address,
        "creation_batch_id": batch_id,
    }
    if hospital.phone:
        payload["phone"] = hospital.phone

    response = await client.post(
        f"{HOSPITAL_API_BASE}/hospitals/",
        json=payload,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def activate_batch(client: httpx.AsyncClient, batch_id: str) -> bool:
    """
    PATCH /hospitals/batch/{batch_id}/activate

    Returns True when the upstream API confirmed activation, False otherwise.
    """
    try:
        response = await client.patch(
            f"{HOSPITAL_API_BASE}/hospitals/batch/{batch_id}/activate",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except (httpx.HTTPStatusError, httpx.RequestError):
        return False


async def get_batch(client: httpx.AsyncClient, batch_id: str) -> list:
    """
    GET /hospitals/batch/{batch_id}

    Returns a list of hospital dicts.  Raises on non-2xx responses.
    """
    response = await client.get(
        f"{HOSPITAL_API_BASE}/hospitals/batch/{batch_id}",
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


async def delete_batch(client: httpx.AsyncClient, batch_id: str) -> bool:
    """
    DELETE /hospitals/batch/{batch_id}

    Used internally during cleanup if a batch needs to be rolled back.
    """
    try:
        response = await client.delete(
            f"{HOSPITAL_API_BASE}/hospitals/batch/{batch_id}",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return True
    except (httpx.HTTPStatusError, httpx.RequestError):
        return False
