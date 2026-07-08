# AI Claims Review Assistant — Cotiviti Intern Hackathon POC

A proof-of-concept demonstrating **Topic 2: Clinical Decision Making and Pattern Recognition
in Health Care** — Chain Reasoning, Agentic Generative AI, Classification, Prediction,
Inference, Clustering, and Time-Series Anomaly Detection for Treatment, Payment, & Operations
(TPO).

## Scenario

A reviewer opens a synthetic healthcare claim and clicks **Analyze**. The system runs four ML
signals (risk classification, payment prediction, provider behavior clustering, billing
anomaly detection), then a **LangGraph** agent chains reasoning over those signals and calls
**Groq** to produce a natural-language recommendation (approve / flag for review / request
more data). Everything is stored in MongoDB and shown on a Next.js dashboard.

## Stack

Next.js (frontend) · FastAPI (backend) · LangGraph + Groq (AI orchestration) · MongoDB
(database) · scikit-learn (classification, prediction, clustering, anomaly detection) on
synthetic data.

## Capability Mapping

| Capability | Where |
|---|---|
| Chain Reasoning | `backend/agent/graph.py::reasoning_node` |
| Agentic Generative AI | `backend/agent/graph.py::recommendation_node` (conditional loop back to fetch more context) |
| Classification | `backend/ml/train_models.py` + `ml/inference.py::classify_claim` (RandomForest → risk label) |
| Prediction | `backend/ml/train_models.py` + `ml/inference.py::predict_payment` (GradientBoosting → paid amount) |
| Inference | Synthesis of all signals into the final `AnalysisResult` in `agent/graph.py` |
| Clustering | `backend/ml/train_models.py` (KMeans on provider behavior) → `frontend/app/providers/[id]` |
| Time-Series Anomaly Detection | `backend/ml/train_models.py` (IsolationForest) → `frontend` anomaly chart |

## Run with Docker (recommended — one command)

The entire app is dockerized: **MongoDB + FastAPI + Next.js**. The backend image
bakes in the synthetic data and trained ML models and seeds MongoDB automatically on
startup.

```
# optional: set your Groq key so the "Run AI Analysis" button works
export GROQ_API_KEY=your_key        # Windows PowerShell: $env:GROQ_API_KEY="your_key"

docker compose up --build -d
```

- App: http://localhost:3000
- API docs: http://localhost:8000/docs
- MongoDB: localhost:27017

Everything else (data generation, model training, DB seeding) happens inside the
containers — no manual steps. `docker compose down` to stop.

> Networking note: browser requests reach the API at `http://localhost:8000`
> (`NEXT_PUBLIC_API_BASE_URL`, baked at build), while Next.js server-side rendering uses
> the internal `http://backend:8000` (`INTERNAL_API_BASE_URL`).

## Run locally without Docker

### 1. Start MongoDB
```
docker compose up -d mongo
```

### 2. Backend
```
cd backend
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy ..\.env.example .env      # then set GROQ_API_KEY (get a free key at console.groq.com)

python -m data_gen.generate_data   # generate synthetic providers/patients/claims/timeseries
python -m ml.train_models          # train classifier, predictor, cluster & anomaly models
python -m data_gen.seed_mongo      # load everything into MongoDB

uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### 3. Frontend
```
cd frontend
npm install
copy .env.local.example .env.local
npm run dev
```
App: http://localhost:3000

## Tests

```
cd backend
venv\Scripts\activate
pip install -r requirements.txt

# unit tests (data generator + ML models) — no services needed
pytest tests/test_data_gen.py tests/test_ml.py

# full suite incl. end-to-end API smoke tests (start the stack first)
docker compose up --build -d
API_BASE_URL=http://localhost:8000 pytest
```

- `tests/test_data_gen.py` — validates synthetic data shape, referential integrity, risk labels
- `tests/test_ml.py` — validates classification/prediction outputs and that all 4 models load
- `tests/test_api_smoke.py` — hits the live API (health, claims, provider cluster & timeseries,
  analyze); auto-skips if the API isn't running

## Verification

- `GET /claims` — browse synthetic claims
- `POST /claims/{id}/analyze` — runs the LangGraph agent (classification, prediction,
  clustering, anomaly detection, chain-of-thought reasoning, and a Groq-generated
  recommendation), persists the result to `claim_analyses`
- `GET /providers/{id}/timeseries` — daily billing series with anomaly flags for the chart
- Next.js dashboard (`/`) → claim detail (`/claims/[id]`) → click **Run AI Analysis** →
  provider page (`/providers/[id]`) shows the cluster label and anomaly chart

## Docs

- **`project_guide.md`** — full walkthrough with project & LangGraph architecture diagrams
  (Mermaid), directory map, endpoint list, and the capability→code map.
- **`project_flow.excalidraw`** — hand-drawn flow diagram (open at excalidraw.com).

## Notes

- All data is synthetic (generated with a fixed seed via `backend/data_gen/generate_data.py`)
  — no real patient data is used.
- This is a hackathon POC, not production software: no auth, no deployment config, models are
  trained offline via a one-time script rather than a full MLOps pipeline.
