# Hospital Bulk Processor

A FastAPI service that accepts CSV uploads and bulk-creates hospital records
via the [Hospital Directory API](https://hospital-directory.onrender.com/docs).

## Project layout

```
hospital-bulk-processor/
├── app/
│   ├── main.py          # FastAPI app + CORS setup
│   ├── config.py        # Environment-based settings
│   ├── schemas.py       # Pydantic models
│   ├── csv_utils.py     # CSV parsing and row validation
│   ├── hospital_api.py  # Async HTTP client for the upstream API
│   ├── processor.py     # Bulk-create orchestration logic
│   ├── store.py         # In-memory batch result store
│   └── routers/
│       └── hospitals.py # Route handlers
├── tests/
│   └── test_bulk.py     # Unit + integration tests
├── sample_hospitals.csv
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Running locally

**Without Docker:**

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**With Docker:**

```bash
docker compose up --build
```

Open http://localhost:8000/docs for the interactive Swagger UI.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `HOSPITAL_API_BASE` | `https://hospital-directory.onrender.com` | Base URL of the upstream API |
| `MAX_CSV_ROWS` | `20` | Maximum hospitals per CSV upload |
| `REQUEST_TIMEOUT` | `15` | Per-request timeout in seconds |

## API endpoints

### `POST /hospitals/bulk`
Upload a CSV and create all hospitals in it.

**CSV format:**
```
name,address,phone
City General,123 Main St,555-0101
Westside Clinic,456 Oak Ave,
```
`phone` is optional.  Maximum 20 rows per upload.

**Response:**
```json
{
  "batch_id": "550e8400-...",
  "total_hospitals": 2,
  "processed_hospitals": 2,
  "failed_hospitals": 0,
  "processing_time_seconds": 1.234,
  "batch_activated": true,
  "hospitals": [
    { "row": 1, "hospital_id": 101, "name": "City General", "status": "created_and_activated" }
  ]
}
```

### `POST /hospitals/bulk/validate`
Dry-run validation — checks the CSV without creating anything.

### `GET /hospitals/bulk/{batch_id}/status`
Retrieve the stored result for a previous batch.

### `GET /hospitals/bulk`
List all batches processed since the server started.

### `GET /health`
Health check.

## Running tests

```bash
pytest tests/ -v
```

To also run the integration tests against the live upstream API:

```bash
INTEGRATION=1 pytest tests/ -v
```

## Deploying to Render

1. Push this repo to GitHub.
2. Create a new **Web Service** on [Render](https://render.com).
3. Set **Build Command** to `pip install -r requirements.txt`.
4. Set **Start Command** to `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
5. Add the environment variables above if you want to override the defaults.
