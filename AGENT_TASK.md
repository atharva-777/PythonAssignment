# Task Brief: Food Trucks Nearby-Search API (KJBN Labs Coding Assignment)

You are building a **production-quality backend service** for a coding assignment. Read this entire
document before writing any code. Follow the phases in order. **Commit after every phase** (commit
instructions are at the end of each phase). Do not squash commits into one giant commit — commit
history is part of the evaluation.

---

## 0. Context (read this first)

- Role being applied for: **Python Backend Developer**.
- Track: **Back-end track** — minimal frontend is fine; auto-generated API docs (Swagger/OpenAPI)
  satisfy the "minimal front-end" requirement.
- Functional spec: **Food Trucks** — "Create a service that tells the user what types of food trucks
  might be found near a specific location on a map."
- Data source: DataSF Food Trucks dataset (Socrata Open Data / SODA API), public, no API key required
  for read-only queries. Dataset name to search for: "Mobile Food Facility Permit" on data.sfgov.org.
- Deadline: same-day. Prioritize a **working, clean, tested** vertical slice over extra features.
- Evaluation criteria (from the client): tech stack knowledge, layered architecture, handling of
  outgoing calls, use of env variables, unit tests, logging, error handling, documentation quality,
  code organization/readability/comments, commit history, and a demo.

---

## 1. Tech Stack (fixed — do not deviate)

- **Language:** Python 3.11+
- **Framework:** FastAPI (gives async support + automatic OpenAPI/Swagger docs at `/docs` for free —
  this is our "minimal frontend")
- **Server:** Uvicorn
- **Database:** SQLite (zero external setup, file-based, fine for this scope)
- **ORM/Query:** Plain `sqlite3` or SQLModel — pick SQLModel if it saves time, otherwise raw SQL with
  a thin repository layer is acceptable
- **Config:** `pydantic-settings` reading from a `.env` file
- **Testing:** `pytest` + FastAPI `TestClient`
- **Logging:** Python's built-in `logging` module, structured (not just `print`)
- **Deployment target:** Render or Railway (free tier), via a `Dockerfile` or native Python build

---

## 2. Project Structure (create exactly this)

```
PythonAssignment/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app instance, startup events, router includes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py            # pydantic-settings, reads .env
│   │   └── logging_config.py    # logging setup
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes/
│   │       ├── __init__.py
│   │       └── food_trucks.py   # route handlers only — no business logic here
│   ├── schemas/
│   │   ├── __init__.py
│   │   └── food_truck.py        # Pydantic request/response models
│   ├── services/
│   │   ├── __init__.py
│   │   └── food_truck_service.py # business logic (distance calc, filtering)
│   ├── repositories/
│   │   ├── __init__.py
│   │   └── food_truck_repository.py # DB access only — no business logic
│   └── db/
│       ├── __init__.py
│       ├── session.py            # DB connection/engine setup
│       └── seed_data.py          # one-time script: download CSV -> load into SQLite
├── tests/
│   ├── __init__.py
│   ├── test_food_truck_service.py
│   └── test_api_food_trucks.py
├── data/
│   └── (downloaded raw CSV goes here, gitignored if large)
├── .env.example
├── .gitignore
├── Dockerfile
├── requirements.txt
├── README.md
└── AGENT_TASK.md   (this file — keep it in the repo for traceability)
```

**Rule:** routes call services, services call repositories, repositories touch the DB. No layer
skips another. No SQL in `routes/` or `services/`. No business logic in `repositories/`.

---

## 3. Phased Execution Plan

### Phase 1 — Project scaffolding & environment
- Set up virtualenv, `requirements.txt` (fastapi, uvicorn, pydantic-settings, sqlmodel or plain
  sqlite3, python-dotenv, pytest, httpx, requests).
- Create the full folder structure above with empty/stub files.
- Create `.env.example` with keys like: `DATABASE_URL`, `LOG_LEVEL`, `DEFAULT_RADIUS_KM`,
  `FOOD_TRUCK_DATA_URL`.
- Create `.gitignore` (venv, `__pycache__`, `.env`, `*.db`, downloaded raw data if large).
- **Commit:** `chore: project scaffolding and environment setup`

### Phase 2 — Data ingestion
- Write `app/db/seed_data.py`: fetches the DataSF food truck dataset (via SODA API endpoint, JSON
  format, e.g. `https://data.sfgov.org/resource/rqzj-sfat.json`), parses fields we need (name,
  food items, latitude, longitude, address, status, schedule/hours if available), and loads them
  into a `food_trucks` SQLite table.
- Handle malformed rows (missing lat/lng) by skipping and logging a warning — do not crash ingestion.
- Make the data source URL configurable via `.env`, not hardcoded.
- **Commit:** `feat: data ingestion script for DataSF food truck dataset`

### Phase 3 — Domain layer (repository + service)
- `food_truck_repository.py`: functions like `get_all()`, `get_by_food_type(type)`, and a query that
  returns all trucks (repository stays dumb — just returns rows/models).
- `food_truck_service.py`: implements the **haversine distance formula** to compute distance from a
  given lat/lng to each truck, filters by `radius_km`, sorts by nearest first, optionally filters by
  food type/keyword.
- Add docstrings explaining the distance calculation.
- **Commit:** `feat: repository and service layer with haversine nearby-search logic`

### Phase 4 — API layer
- `schemas/food_truck.py`: `FoodTruckOut` (id, name, food_items, lat, lng, address, distance_km),
  `NearbyQueryParams` (lat, lng, radius_km with sane default from config, optional food_type filter).
- `api/routes/food_trucks.py`:
  - `GET /food-trucks` — list all (optionally paginated).
  - `GET /food-trucks/nearby?lat=&lng=&radius_km=&food_type=` — core feature.
  - Validate lat/lng ranges (-90..90, -180..180); return `422`/`400` with clear error message on
    invalid input.
- Wire routes into `main.py` with a router prefix, e.g. `/api/v1`.
- **Commit:** `feat: REST API endpoints for listing and nearby food truck search`

### Phase 5 — Logging & error handling
- Configure logging in `core/logging_config.py`: log level from `.env`, log to stdout, include
  timestamps, log every request's key params and outcome (found N trucks / error).
- Add a global exception handler in `main.py` for unhandled errors → returns clean JSON `500`
  without leaking stack traces to the client, but logs full trace internally.
- **Commit:** `feat: structured logging and centralized error handling`

### Phase 6 — Unit & integration tests
- `test_food_truck_service.py`: test haversine calc against known distances, test radius filtering,
  test food_type filtering.
- `test_api_food_trucks.py`: use `TestClient` to hit `/food-trucks/nearby` with valid and invalid
  params, assert status codes and response shape.
- Aim for meaningful coverage of the core logic, not 100% coverage padding.
- **Commit:** `test: unit and API tests for nearby food truck search`

### Phase 7 — Documentation
- Write `README.md` including:
  - Project overview and which functional spec option was chosen (Food Trucks) and why.
  - Architecture diagram/explanation (routes → services → repositories → db).
  - Setup instructions (clone, venv, install, `.env` setup, run seed script, run server).
  - API documentation: link to `/docs` (Swagger UI) plus example curl requests for both endpoints.
  - How to run tests (`pytest`).
  - **Developer details section** (name, contact, role applying for).
  - **A note on stack experience** — how familiar the developer is with FastAPI/Python/SQLite (be
    honest, per the assignment's instructions).
  - Note any boilerplate vs. hand-written code, if a generator/template was used anywhere.
- **Commit:** `docs: complete README with setup, architecture, and API usage`

### Phase 8 — Containerization & deployment
- Write a `Dockerfile` (slim python base image, copy app, install requirements, run uvicorn).
- Deploy to Render or Railway free tier. Add the live URL to the README.
- **Commit:** `chore: add Dockerfile and deployment configuration`

### Phase 9 — Final pass
- Re-read code for unused imports, dead code, missing type hints, and inconsistent naming.
- Confirm `.env` is not committed (only `.env.example`).
- Manually test both endpoints against the deployed URL.
- **Commit:** `chore: final cleanup and polish before submission`

---

## 4. Commit Discipline (important)

- Commit **at the end of every phase above at minimum** — smaller, more frequent commits within a
  phase are fine and encouraged (e.g., separate commits for schema vs. route within Phase 4).
- Use **conventional commit prefixes**: `feat:`, `fix:`, `chore:`, `docs:`, `test:`, `refactor:`.
- Write commit messages that describe *what* and briefly *why*, not just "update files".
- Never commit `.env`, virtual environments, `__pycache__`, or the raw downloaded dataset if it's
  large.
- Do not force-push or rewrite history — a clean, linear, honest commit history is part of what's
  being evaluated.

---

## 5. Definition of Done

- [ ] `GET /food-trucks/nearby?lat=..&lng=..&radius_km=..` returns correctly sorted, distance-annotated
      results from real DataSF data.
- [ ] Invalid input (bad lat/lng, negative radius) returns a clear 4xx error, not a crash.
- [ ] Swagger docs at `/docs` are functional and demonstrate all endpoints.
- [ ] `pytest` passes with no failures.
- [ ] Logging output shows request handling and errors clearly.
- [ ] `.env.example` present; no secrets committed.
- [ ] README is complete per Phase 7 checklist.
- [ ] App is deployed and reachable at a public URL.
- [ ] Commit history reflects the phases above, not a single commit.

---

## 6. If Time Runs Out

Priority order if you must cut scope (cut from the bottom up):
1. Skip Docker + deployment polish — a working local demo + README instructions is still acceptable,
   but **try hardest not to cut deployment entirely** since "Host it!" is explicit in the spec.
2. Reduce test coverage to just the haversine/service logic (skip full API integration tests).
3. Skip food_type filtering — nearby search by lat/lng/radius alone is the core requirement.
4. Never skip: working nearby endpoint, README, logging, error handling, and committing frequently.
