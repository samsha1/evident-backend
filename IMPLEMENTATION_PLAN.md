# Evident MVP — Implementation Plan

> **Reference:** [ARCHITECTURE.md](file:///Users/samrat/Documents/samrat/projects/evident/evident-backend/ARCHITECTURE.md)  
> **Approach:** Restructure the existing `evident-backend` repo from Vercel serverless to a Hetzner-deployed Docker Compose stack. Build bottom-up: infrastructure → data layer → crawlers → sentiment → SSE streaming → auth → deployment. Each phase is independently testable.

## Scope

**In:**
- Project restructure to match ARCHITECTURE.md layout
- Docker Compose stack (Caddy, FastAPI, Postgres, Redis, Prefect)
- Postgres schema + Alembic migrations (users, products, reviews, product_scores)
- SOLID crawler framework (strategies, parsers, platform crawlers)
- Reddit crawler (official API, MVP-first)
- YouTube crawler (Data API v3)
- Amazon crawler (aiohttp scrape strategy, your existing approach)
- Sentiment service (local transformer primary, LLM fallback)
- Verdict computation engine
- SSE streaming endpoint with create_task + Queue
- Three-tier Redis cache (fresh/stale/miss)
- Distributed lock + pub/sub coalescing
- Google OAuth authentication
- Redis-based rate limiting
- Hetzner CX32 deployment (Docker Compose + Caddy)

**Out:**
- Chrome extension (separate repo, separate plan)
- X/Twitter crawler
- Product name search / fuzzy entity resolution
- Paid tiers / Stripe
- CI/CD pipeline (post-MVP)
- Load testing (pre-launch, not MVP)

---

## Phase 1 — Project Restructure + Infrastructure

> Goal: Working Docker Compose stack with empty FastAPI, Postgres, Redis, health check passing.

- [ ] 1.1 Restructure `evident-backend/` directory to match ARCHITECTURE.md layout (move crawlers, create services/, crawlers/strategies/, crawlers/platforms/, services/sentiment/)
- [ ] 1.2 Remove Vercel artifacts (`vercel.json`, `.vercelignore`, Mangum dependency, `apps/.vercel/`)
- [ ] 1.3 Write `Dockerfile` for FastAPI (Python 3.12, uvicorn, 2 workers, model volume mount)
- [ ] 1.4 Write `docker-compose.yml` (Caddy, FastAPI, Postgres 15, Redis 7, volumes)
- [ ] 1.5 Write `Caddyfile` (reverse proxy to FastAPI, auto-TLS placeholder for local dev)
- [ ] 1.6 Update `pyproject.toml` — remove Mangum, add SSE/auth dependencies
- [ ] 1.7 Verify: `docker compose up` → `curl localhost/api/v1/health` returns `{"status": "ok"}`

---

## Phase 2 — Data Layer

> Goal: Postgres schema live, Alembic migrations working, SQLAlchemy async models operational.

- [ ] 2.1 Write SQLAlchemy async models: `User`, `Product`, `Review`, `ProductScore`
- [ ] 2.2 Set up Alembic with async driver (`asyncpg`), generate initial migration
- [ ] 2.3 Write `core/database.py` — async engine, session factory, `get_db` dependency
- [ ] 2.4 Write `core/redis.py` — Redis client singleton, connection pool
- [ ] 2.5 Verify: `alembic upgrade head` creates all 4 tables, `docker compose exec postgres psql` confirms schema

---

## Phase 3 — Crawler Framework + First Crawler (Reddit)

> Goal: SOLID crawler framework built. Reddit crawler returning real reviews for a test ASIN.

- [ ] 3.1 Write base protocols: `CrawlStrategy`, `PlatformParser`, `RawResponse`, `RawReview`, `CrawlerResult`
- [ ] 3.2 Write `PlatformCrawler` class (strategy + parser + timeout + queue push)
- [ ] 3.3 Write `ApiStrategy` (aiohttp GET/POST with auth headers)
- [ ] 3.4 Write `RedditJsonParser` (extract posts + comments from Reddit API JSON)
- [ ] 3.5 Write `factory.py` — `build_crawlers()` assembles crawlers from config
- [ ] 3.6 Write Reddit OAuth2 client credentials flow in `ApiStrategy`
- [ ] 3.7 Verify: pytest test — given ASIN "B0D5CJ3WY4", Reddit crawler returns >0 reviews via queue

---

## Phase 4 — Remaining Crawlers + Sentiment + Verdict

> Goal: All 3 crawlers working. Sentiment model loaded. Verdict computation functional.

- [ ] 4.1 Write `YouTubeApiParser` + YouTube crawler (search + commentThreads)
- [ ] 4.2 Write `AiohttpScrapeStrategy` + `AmazonHtmlParser` + Amazon crawler
- [ ] 4.3 Write `SentimentProvider` protocol, `LocalTransformerProvider` (load model at startup)
- [ ] 4.4 Write `LlmApiProvider` fallback (OpenAI/Anthropic batch sentiment)
- [ ] 4.5 Write `SentimentService` (primary + fallback chain)
- [ ] 4.6 Write `verdict.py` — `compute_verdict()` with weighted scoring + confidence
- [ ] 4.7 Verify: end-to-end test — 3 crawlers → sentiment → verdict for a known ASIN

---

## Phase 5 — SSE Streaming + Cache + Auth + Rate Limiting

> Goal: Full hot-path working. Authenticated SSE endpoint streams partial results, caches results, enforces rate limits.

- [ ] 5.1 Write `services/orchestrator.py` — create_task + Queue drain loop + SSE event generator
- [ ] 5.2 Write `routers/product.py` — `GET /api/v1/product/{asin}/stream` SSE endpoint
- [ ] 5.3 Write `services/cache.py` — three-tier cache (fresh/stale/miss), distributed lock (SET NX), pub/sub coalescing
- [ ] 5.4 Write `core/security.py` — Google OAuth JWT validation, `get_current_user` dependency
- [ ] 5.5 Write `routers/auth.py` — `POST /api/v1/auth/google` (exchange code for JWT, upsert user)
- [ ] 5.6 Write `services/rate_limiter.py` — Redis INCR with daily TTL, 429 response
- [ ] 5.7 Verify: integration test — authenticated SSE request returns streaming events for each crawler + final verdict

---

## Phase 6 — Prefect Background + Hetzner Deployment

> Goal: Background recrawls running. Production deployment live on Hetzner with TLS.

- [ ] 6.1 Write `pipelines/flows/recrawl.py` — Prefect flow that recrawls stale products
- [ ] 6.2 Add Prefect worker to `docker-compose.yml`
- [ ] 6.3 Provision Hetzner CX32, install Docker, clone repo
- [ ] 6.4 Configure `.env.production` with real API keys (Reddit, YouTube, Google OAuth client)
- [ ] 6.5 Update `Caddyfile` with production domain + auto-TLS
- [ ] 6.6 `docker compose up -d` on Hetzner, verify all services healthy
- [ ] 6.7 Verify: `curl https://api.evident.app/api/v1/health` returns `{"status": "ok"}`

---

## Open Questions

1. **Domain name:** Do you have `evident.app` or similar registered? Caddy needs a domain for auto-TLS.
2. **Google OAuth client:** Do you have a Google Cloud project with OAuth consent screen configured? Needed for Phase 5.
3. **Sentiment model selection:** Confirm `cardiffnlp/twitter-roberta-base-sentiment-latest` or do you prefer a different model?
