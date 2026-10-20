# ElderLife AI

> **Current status: Phase 1 — project skeleton only.**
> No application feature is working yet. This repository currently contains folders,
> documentation, and configuration templates. Do not treat anything here as a finished product.

ElderLife AI is a beginner-friendly graduation project: a system that helps monitor the
well-being of elderly people at home. When finished, it will:

- detect **falls** from sensor data,
- recognize daily **activities** (walking, resting, cooking, ...),
- spot **behavioral anomalies** (unusual routines that may indicate health changes),
- manage **residents and care plans**,
- raise **alerts** for caregivers,
- and produce **analytics** that can be opened in Power BI.

---

## Technology stack (planned)

| Layer | Technology | Why |
|---|---|---|
| Frontend | React + TypeScript + Vite | Modern, typed, fast dev server |
| Backend | Python + FastAPI | Simple, fast, auto-generated API docs |
| Database | PostgreSQL | Reliable relational database |
| ORM / Migrations | SQLAlchemy + Alembic | Standard Python DB tools |
| AI / ML | Python (scikit-learn, etc.) | Datasets are tabular/sensor based |
| Analytics | SQL views + CSV/Parquet exports | Easy to load into Power BI |
| Deployment | Docker Compose | One command to run the whole stack |

---

## Repository structure

```
ElderLife-AI/
├── frontend/                 # React + TypeScript + Vite web app
├── backend/                  # FastAPI application (REST API)
├── ai/                       # Machine-learning code, grouped by problem
│   ├── fall_detection/       #   fall detection models & logic
│   ├── activity_recognition/ #   daily activity classification
│   └── behavioral_analysis/  #   routine / anomaly detection
├── data/                     # Datasets live here (mostly git-ignored)
│   ├── raw/                  #   original downloaded files — never edited
│   ├── processed/            #   cleaned data produced by scripts
│   └── sample/               #   small hand-made examples for tests
├── analytics/
│   ├── sql/                  #   SQL views/queries feeding Power BI
│   └── exports/              #   generated CSV/Parquet files (git-ignored)
├── docs/                     # Architecture, API contract, roadmap, datasets
├── tests/                    # Cross-cutting tests (pytest + frontend tests)
├── docker-compose.yml        # Runs PostgreSQL (more services added later)
├── .env.example              # Placeholder environment variables — copy to .env
├── .gitignore                # Keeps secrets, data, and junk out of Git
└── README.md                 # This file
```

Every major folder contains its own `README.md` explaining what belongs there.

---

## Prerequisites

| Tool | Required for | Status on this machine |
|---|---|---|
| Node.js 20+ | frontend | ✅ installed (v24.13.1) |
| npm | frontend | ✅ installed (11.8.0) |
| Python 3.11–3.13 | backend, AI | ⚠️ 3.15.0 installed (see note below) |
| pip | Python packages | ✅ installed (26.2.1) |
| Git | version control | ✅ installed (2.53.0) |
| VS Code | editor | ✅ installed (1.142.0) |
| Docker Desktop | docker-compose.yml | ❌ **missing** |
| PostgreSQL | local database | ❌ **missing** (`psql` not found) |

**Note on Python 3.15:** it was released recently, so some ML packages
(numpy, pandas, scikit-learn, PyTorch) may not have pre-built wheels for it yet.
If a package install fails in a later phase, install Python 3.12 or 3.13 alongside it
(from python.org or `winget install Python.Python.3.12`) and create the virtual
environment with that version instead. Nothing needs to be installed for Phase 1.

**Note on Docker / PostgreSQL:** both are missing. That is fine for Phase 1.
You will be asked before anything is installed. Options will be presented in Phase 2:
either install Docker Desktop (runs PostgreSQL in a container) or install PostgreSQL
directly on Windows.

---

## Getting started

Not applicable yet — there is nothing to run. Later phases will add:

```bash
# Phase 2+ (not runnable today)
python -m venv .venv          # Python virtual environment
npm create vite@latest        # frontend scaffold
docker compose up -d db       # start PostgreSQL (requires Docker)
```

---

## Datasets

Three public research datasets will be used later (UP-Fall, CASAS, UCI HAR).
**None have been downloaded yet**, and no model has been trained.
Each dataset will be documented in [`docs/datasets/`](docs/datasets/README.md)
(source URL, license, format, labels, preprocessing, limitations) *before* it is used.

---

## Documentation

| Document | Contents |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Mermaid diagram + component explanation |
| [docs/api-contract.md](docs/api-contract.md) | Proposed API between frontend, backend, AI |
| [docs/roadmap.md](docs/roadmap.md) | Milestones for every phase |
| [docs/datasets/README.md](docs/datasets/README.md) | Dataset documentation template + index |

---

## Honesty rules for this project

1. Features are only described as "working" when they actually run.
2. No fake production data is committed.
3. Real credentials never live in this repository — only in your local `.env`.
4. Datasets and trained model artifacts are not committed to Git.
