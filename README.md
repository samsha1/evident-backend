# ReviewAgg Platform

ReviewAgg is a service-oriented cross-platform review aggregator. It crawls product reviews and ratings across multiple social and e-commerce platforms (Amazon, Reddit, YouTube, TikTok, Instagram), normalizes them via a Medallion Architecture data pipeline, computes AI-driven product sentiment scores, and serves them via a scalable frontend widget and dashboard.

## 🏗️ Monorepo Architecture

This project is built as a strict monorepo, separating concerns across API, Frontend, Data Pipelines, and Shared types:

```
evident-backend/
├── apps/
│   ├── web/          ← Next.js 15 (App Router) — product pages, widgets, dashboards
│   └── api/          ← FastAPI with Mangum adapter (Vercel Serverless Functions)
├── packages/
│   └── shared/       ← Shared Pydantic / SQLAlchemy data models and TS types
├── pipelines/        ← Prefect flows, social crawlers, dbt transforms (Railway/Render)
└── vercel.json       ← Vercel deployment configurations and crons
```

## 🛠️ Tech Stack & Infrastructure

- **Frontend & API**: Vercel (Next.js 15 App Router + Serverless FastAPI via Mangum)
- **Database**: Neon (Serverless PostgreSQL)
- **Cache**: Vercel KV (Upstash Redis)
- **Object Storage**: Cloudflare R2 (S3-compatible, Bronze Layer)
- **Search**: Typesense (Self-hosted on Railway)
- **Pipelines / Jobs**: Prefect OSS (Railway / Render)
- **Package Management**: Poetry (Python) & npm (Node.js)

## 🗄️ Data Layer (Medallion Architecture)

1. **Bronze Layer**: Raw, unstructured HTML/JSON scraped from platforms, stored directly in Cloudflare R2. Never mutated.
2. **Silver Layer**: Normalized review structures (Standardized 0-1 ratings, formatted authors, cleaned text), mapped via `EntityResolver` and stored in PostgreSQL.
3. **Gold Layer**: Aggregated AI-scored metrics (`ProductScore`) exposed dynamically by FastAPI.

## 🚀 Getting Started Locally

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- [Poetry](https://python-poetry.org/)

### 1. Environment Setup

Clone `.env.example` into `.env` at the root and fill in your local or production keys.

```bash
cp .env.example .env
```

### 2. Start Infrastructure

Boot up the local PostgreSQL database, Redis instance, Typesense search, and Prefect server.

```bash
docker-compose up -d
```

### 3. Initialize the Backend (FastAPI)

```bash
# Install dependencies
poetry install

# Apply Alembic Migrations
poetry run alembic upgrade head

# Start FastAPI development server
cd apps/api/src
poetry run uvicorn main:app --reload --port 8000
```

### 4. Initialize the Frontend (Next.js)

```bash
cd apps/web
npm install
npm run dev
```

Your API will be running at `http://localhost:8000` (docs at `/docs`) and the Frontend at `http://localhost:3000`.

## 📜 Development Rules

- **Schema Changes**: Do NOT manually alter tables. Modify Pydantic/SQLAlchemy models in `packages/shared/models` and use Alembic (`poetry run alembic revision --autogenerate -m "..."`).
- **Commits**: Strictly follow conventional commits (e.g., `feat(api): add new product route`).
- **Dependencies**: Add new Python dependencies via `poetry add <package>`, then immediately update the Vercel requirements file: `poetry export -f requirements.txt --output requirements.txt --without-hashes`.
