# Food Trucks Nearby-Search API

A production-minded FastAPI backend for the KJBN Labs coding assignment. It uses San Francisco's public **Mobile Food Facility Permit** dataset to answer the Food Trucks functional spec: *what types of food trucks might be found near a location on a map?*

The Food Trucks option was chosen because it has a real, public source of geocoded data and makes the assignment's core concerns—outgoing API calls, data validation, persistence, geographical search, and an HTTP API—easy to demonstrate in one focused service.

## Features

- Downloads the live DataSF Mobile Food Facility Permit dataset through its Socrata SODA JSON API.
- Validates latitude/longitude data, logs and skips malformed rows, and atomically refreshes SQLite data.
- Finds trucks within a requested radius using the Haversine great-circle distance formula.
- Optionally filters food descriptions by a case-insensitive keyword such as `taco` or `coffee`.
- Returns results ordered nearest-first with an annotated `distance_km` value.
- Provides automatic OpenAPI documentation through FastAPI's Swagger UI.
- Emits structured JSON logs and returns a safe JSON response for unexpected errors.

## Architecture

```text
HTTP client / Swagger UI
          |
          v
FastAPI routes (/api/v1/food-trucks)
          |
          v
FoodTruckService
  - Haversine distance
  - radius and keyword filtering
  - nearest-first sorting
          |
          v
FoodTruckRepository
  - parameterized SQLite queries
          |
          v
SQLite food_trucks table <--- seed_data.py <--- DataSF SODA API
```

The layers are deliberately separated: route handlers translate HTTP concerns, the service owns business rules, and the repository is the only layer that runs SQL.

## Prerequisites

- Python 3.11 or later
- Internet access for the initial DataSF download

## Local setup

1. Clone the repository and enter its directory.

   ```bash
   git clone <your-repository-url>
   cd PythonAssignment
   ```

2. Create and activate a virtual environment.

   ```bash
   # Windows PowerShell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

   # macOS/Linux
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install dependencies and create your local configuration.

   ```bash
   pip install -r requirements.txt
   copy .env.example .env  # PowerShell/cmd on Windows
   # cp .env.example .env  # macOS/Linux
   ```

4. Download the real DataSF dataset and load it into the local SQLite database.

   ```bash
   python -m app.db.seed_data
   ```

   A successful run prints its loaded/skipped totals. The generated `food_trucks.db` and any raw downloaded data are ignored by Git.

5. Start the API server.

   ```bash
   uvicorn app.main:app --reload
   ```

The API is then available at `http://127.0.0.1:8000`.

## Configuration

Copy `.env.example` to `.env`; do not commit `.env`.

| Variable | Purpose | Default |
| --- | --- | --- |
| `DATABASE_URL` | SQLite database URL | `sqlite:///./food_trucks.db` |
| `LOG_LEVEL` | Python logging level | `INFO` |
| `DEFAULT_RADIUS_KM` | Nearby endpoint's fallback radius | `5.0` |
| `FOOD_TRUCK_DATA_URL` | Configurable DataSF SODA JSON endpoint | DataSF Mobile Food Facility Permit |
| `FOOD_TRUCK_REQUEST_TIMEOUT_SECONDS` | Timeout for DataSF HTTP requests | `30` |

## API documentation and examples

Interactive Swagger UI is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) while the server is running. The versioned API prefix is `/api/v1`.

### List food trucks

`GET /api/v1/food-trucks`

```bash
curl "http://127.0.0.1:8000/api/v1/food-trucks?offset=0&limit=10"
```

`offset` defaults to `0`, and `limit` defaults to `100` (maximum `100`). An optional `food_type` keyword can narrow the list.

### Search nearby food trucks

`GET /api/v1/food-trucks/nearby?lat=&lng=&radius_km=&food_type=`

```bash
curl "http://127.0.0.1:8000/api/v1/food-trucks/nearby?lat=37.7749&lng=-122.4194&radius_km=2&food_type=taco"
```

`lat` must be between `-90` and `90`; `lng` between `-180` and `180`; and `radius_km` must be non-negative. Invalid input returns FastAPI's clear `422` validation response. If omitted, `radius_km` takes `DEFAULT_RADIUS_KM` from the environment.

Nearby results include the following shape and are sorted by `distance_km` ascending:

```json
[
  {
    "id": 1,
    "name": "Example Vendor",
    "food_items": "Tacos; Burritos",
    "lat": 37.7749,
    "lng": -122.4194,
    "address": "1 Market St",
    "status": "APPROVED",
    "schedule": "https://...",
    "facility_type": "Truck",
    "distance_km": 0.0
  }
]
```

## Testing

Run the deterministic test suite with:

```bash
pytest -q
```

The tests use in-memory or temporary SQLite datasets; they do not call DataSF. Coverage includes the Haversine calculation, radius filtering, food-keyword filtering, sort order, HTTP response shape, pagination, and invalid query parameters.

## Data source

The ingestion command reads the public [DataSF Mobile Food Facility Permit dataset](https://data.sfgov.org/Economy-and-Community/Mobile-Food-Facility-Permit/rqzj-sfat) using its configurable SODA JSON endpoint. The local schema retains vendor name, food items, WGS84 coordinates, address, permit status, schedule URL, and facility type.

## Developer details

- **Name:** Atharva Jadhav
- **Contact:** jadhavatharva499@gmail.com
- **Role applying for:** Python Backend Developer

### Stack experience

Familiar with Python, FastAPI, and SQLite. This project applies that familiarity to a layered backend with Pydantic configuration, external HTTP ingestion, SQLite persistence, dependency-injected request handling, structured logging, and pytest/TestClient coverage.

### Boilerplate and templates

No project generator or code template was used. The application structure and implementation were created specifically for this assignment. FastAPI's `/docs` interface is framework-provided Swagger/OpenAPI documentation rather than a custom frontend.

## Deployment

The repository includes a Dockerfile for deployment to Render or Railway. After deployment, add the public service URL here and replace the local `/docs` link above with the hosted documentation URL.
