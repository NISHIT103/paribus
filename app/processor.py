"""
processor.py
------------
Orchestrates the full bulk-create workflow:

  1. Generate a batch UUID
  2. POST each hospital to the upstream API (concurrently, but gated so we
     don't hammer the upstream server)
  3. PATCH .../activate if all hospitals were created successfully
  4. Persist the result and return it
"""

import asyncio
import time
import uuid
from typing import List

import httpx

from app import hospital_api, store
from app.schemas import BulkCreateResponse, HospitalResult, HospitalRow

# How many hospitals to send to the upstream API at the same time.
# Keeping this low is polite to the shared test server.
CONCURRENCY = 5


async def process_bulk(hospitals: List[HospitalRow]) -> BulkCreateResponse:
    batch_id = str(uuid.uuid4())
    results: List[HospitalResult] = [None] * len(hospitals)  # type: ignore
    start = time.perf_counter()

    async with httpx.AsyncClient() as client:
        # ---------- Step 1: create all hospitals ----------
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def create_one(index: int, hospital: HospitalRow) -> None:
            async with semaphore:
                try:
                    data = await hospital_api.create_hospital(client, hospital, batch_id)
                    results[index] = HospitalResult(
                        row=index + 1,
                        hospital_id=data.get("id"),
                        name=hospital.name,
                        status="created",
                    )
                except httpx.HTTPStatusError as exc:
                    results[index] = HospitalResult(
                        row=index + 1,
                        name=hospital.name,
                        status="failed",
                        error=f"HTTP {exc.response.status_code}: {exc.response.text[:200]}",
                    )
                except httpx.RequestError as exc:
                    results[index] = HospitalResult(
                        row=index + 1,
                        name=hospital.name,
                        status="failed",
                        error=f"Network error: {exc}",
                    )

        await asyncio.gather(*[create_one(i, h) for i, h in enumerate(hospitals)])

        # ---------- Step 2: activate batch if everything went through ----------
        failed = [r for r in results if r.status == "failed"]
        activated = False

        if not failed:
            activated = await hospital_api.activate_batch(client, batch_id)
            if activated:
                for r in results:
                    r.status = "created_and_activated"

    elapsed = round(time.perf_counter() - start, 3)

    response = BulkCreateResponse(
        batch_id=batch_id,
        total_hospitals=len(hospitals),
        processed_hospitals=len(hospitals) - len(failed),
        failed_hospitals=len(failed),
        processing_time_seconds=elapsed,
        batch_activated=activated,
        hospitals=results,
    )

    store.save_batch(response)
    return response
