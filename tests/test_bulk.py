"""
tests/test_bulk.py
------------------
Tests for CSV parsing, validation, and the bulk-create endpoint.

Integration tests that touch the upstream API are skipped by default — set
INTEGRATION=1 in the environment to run them.
"""

import os
import io
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.csv_utils import parse_csv
from app.schemas import HospitalRow

client = TestClient(app)

INTEGRATION = os.getenv("INTEGRATION", "0") == "1"


# ── CSV parsing unit tests ───────────────────────────────────────────────────

class TestCsvParsing:
    def test_parses_valid_csv_with_phone(self):
        raw = b"name,address,phone\nCity General,123 Main St,555-0100\n"
        rows, errors = parse_csv(raw)
        assert errors == []
        assert len(rows) == 1
        assert rows[0].name == "City General"
        assert rows[0].phone == "555-0100"

    def test_parses_valid_csv_without_phone(self):
        raw = b"name,address\nWestside Clinic,99 Elm Ave\n"
        rows, errors = parse_csv(raw)
        assert errors == []
        assert rows[0].phone is None

    def test_missing_required_column(self):
        raw = b"name,phone\nSomebody Hospital,555-9999\n"
        rows, errors = parse_csv(raw)
        assert any("address" in e for e in errors)
        assert rows == []

    def test_empty_file(self):
        rows, errors = parse_csv(b"")
        assert errors  # should have at least one error

    def test_exceeds_max_rows(self):
        # Build a CSV with 21 rows
        lines = ["name,address"] + [f"Hospital {i},Address {i}" for i in range(21)]
        raw = "\n".join(lines).encode()
        rows, errors = parse_csv(raw)
        assert any("maximum" in e.lower() for e in errors)
        assert rows == []

    def test_blank_name_row_produces_error(self):
        raw = b"name,address\n,123 Nowhere St\n"
        rows, errors = parse_csv(raw)
        assert any("name" in e.lower() for e in errors)

    def test_header_names_are_case_insensitive(self):
        raw = b"NAME,ADDRESS\nMed Center,1 Park Rd\n"
        rows, errors = parse_csv(raw)
        assert errors == []
        assert len(rows) == 1


# ── Validation endpoint tests ────────────────────────────────────────────────

class TestValidateEndpoint:
    def _upload(self, content: bytes, filename="test.csv"):
        return client.post(
            "/hospitals/bulk/validate",
            files={"file": (filename, io.BytesIO(content), "text/csv")},
        )

    def test_valid_csv(self):
        raw = b"name,address\nGood Hospital,10 Hope St\n"
        resp = self._upload(raw)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is True
        assert body["total_rows"] == 1
        assert body["errors"] == []

    def test_invalid_csv_missing_column(self):
        raw = b"name\nOnly Name\n"
        resp = self._upload(raw)
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False
        assert body["errors"]

    def test_empty_file(self):
        resp = self._upload(b"  ")
        assert resp.status_code == 200
        body = resp.json()
        assert body["valid"] is False


# ── Bulk create endpoint tests (mocked) ─────────────────────────────────────

class TestBulkCreateEndpoint:
    def _upload(self, content: bytes):
        return client.post(
            "/hospitals/bulk",
            files={"file": ("hospitals.csv", io.BytesIO(content), "text/csv")},
        )

    @patch("app.processor.hospital_api.create_hospital")
    @patch("app.processor.hospital_api.activate_batch")
    def test_successful_bulk_create(self, mock_activate, mock_create):
        mock_create.return_value = {"id": 1, "name": "Test Hospital", "active": False}
        mock_activate.return_value = True

        raw = b"name,address\nTest Hospital,1 Test St\n"
        resp = self._upload(raw)

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_hospitals"] == 1
        assert body["processed_hospitals"] == 1
        assert body["failed_hospitals"] == 0
        assert body["batch_activated"] is True
        assert body["hospitals"][0]["status"] == "created_and_activated"

    @patch("app.processor.hospital_api.create_hospital")
    @patch("app.processor.hospital_api.activate_batch")
    def test_partial_failure_skips_activation(self, mock_activate, mock_create):
        import httpx
        mock_create.side_effect = httpx.RequestError("connection refused")
        mock_activate.return_value = False

        raw = b"name,address\nBad Hospital,1 Fail St\n"
        resp = self._upload(raw)

        assert resp.status_code == 200
        body = resp.json()
        assert body["failed_hospitals"] == 1
        assert body["batch_activated"] is False

    def test_invalid_csv_returns_422(self):
        raw = b"name\nMissing Address Column\n"
        resp = self._upload(raw)
        assert resp.status_code == 422

    def test_empty_file_returns_400(self):
        resp = self._upload(b"")
        assert resp.status_code == 400


# ── Batch status endpoint tests ──────────────────────────────────────────────

class TestBatchStatusEndpoint:
    def test_missing_batch_returns_404(self):
        resp = client.get("/hospitals/bulk/nonexistent-id/status")
        assert resp.status_code == 404

    @patch("app.processor.hospital_api.create_hospital")
    @patch("app.processor.hospital_api.activate_batch")
    def test_status_after_bulk_create(self, mock_activate, mock_create):
        mock_create.return_value = {"id": 42, "name": "Status Test", "active": False}
        mock_activate.return_value = True

        raw = b"name,address\nStatus Test,5 Query Ln\n"
        create_resp = client.post(
            "/hospitals/bulk",
            files={"file": ("h.csv", io.BytesIO(raw), "text/csv")},
        )
        batch_id = create_resp.json()["batch_id"]

        status_resp = client.get(f"/hospitals/bulk/{batch_id}/status")
        assert status_resp.status_code == 200
        assert status_resp.json()["batch_id"] == batch_id


# ── Integration tests (skipped unless INTEGRATION=1) ────────────────────────

@pytest.mark.skipif(not INTEGRATION, reason="Set INTEGRATION=1 to run against live API")
class TestIntegration:
    def test_real_bulk_create(self):
        raw = b"name,address,phone\nIntegration Hospital,1 Live St,555-0001\n"
        resp = client.post(
            "/hospitals/bulk",
            files={"file": ("live.csv", io.BytesIO(raw), "text/csv")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["batch_activated"] is True
        assert body["failed_hospitals"] == 0
