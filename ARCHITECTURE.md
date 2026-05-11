# Evident — Architecture Design Document

> **Version:** 1.0 — MVP  
> **Date:** 2026-05-10  
> **Status:** Approved (brainstorming complete)

---

## 1. Understanding Summary

1. **What:** A Chrome extension (Manifest V3) that aggregates product reviews from Reddit, YouTube, and Amazon, runs local sentiment analysis, and delivers a "Buy / Don't Buy" verdict via SSE streaming.
2. **Why:** No single tool gives consumers honest, cross-platform product feedback. Review systems are siloed and gamed.
3. **Who:** Amazon shoppers who want unbiased opinions before purchasing. Also retailers who want to know what the world thinks about their product.
4. **Trigger:** User on Amazon product page → extension detects ASIN → Google OAuth ensures authenticated user → rate limit check → request fires to backend → SSE streams partial results back.
5. **Infrastructure:** Single Hetzner CX32 (4 vCPU, 8GB, ~€9/mo). Self-hosted FastAPI, Redis, Postgres, Prefect, local sentiment model. No serverless.
6. **Hot path:** `asyncio.create_task()` + `asyncio.Queue` runs Reddit + YouTube + Amazon crawlers as independent tasks with per-crawler timeouts. Each crawler pushes results to a shared queue as it completes. SSE handler drains the queue and streams partial results immediately. Graceful degradation — if any crawler fails/times out, verdict computes from available data. First partial result within ~1.5s, full verdict within 8-12s.
7. **Background path:** Prefect for scheduled recrawls of cached products only. No hot-path orchestration.
8. **User management:** Google OAuth. Rate cap of 5-10 requests/day per user (configurable). Exception list for admin/test accounts. Enforced via Redis INCR with daily TTL.
9. **Data sources for MVP:** Reddit (official API, free), YouTube (Data API v3, free), Amazon (own scraping infrastructure with proxies).
10. **Sentiment:** Local transformer model (~500MB, CPU) as primary. LLM API (OpenAI/Anthropic) as fallback when local model fails or times out.
11. **Deferred to post-MVP:** X/Twitter, product name search, fuzzy entity resolution, Firefox/Safari, multi-server HA, paid tiers.

---

## 2. Assumptions

- ASIN is the canonical product identifier. Product title scraped from Amazon is used as search query for Reddit/YouTube.
- Amazon crawler is the slowest and most failure-prone (proxy/CAPTCHA risk). Architecture handles partial verdicts from available sources.
- Sentiment model: ~1.5GB RAM resident. Leaves ~5-6GB for everything else on CX32.
- Caddy handles TLS termination with Let's Encrypt auto-cert.
- Total monthly cost target: less than €20/mo (Hetzner €9 + domain ~€1 + no paid APIs).
- Rate limit: 5-10 lookups/day per user. Admin exceptions stored in Postgres `users.tier` field.
- Cache hit on popular products expected to reduce crawl load by 40-60% after warmup.
- No user authentication bypass — every request requires a valid Google JWT.
- YouTube free quota (~65 full lookups/day) is sufficient with aggressive caching.

---

## 3. Decision Log

| # | Decision | Alternatives Considered | Rationale |
|---|---|---|---|
| 1 | ASIN-only trigger for MVP | Product name search, URL input | Deterministic key, no entity resolution needed |
| 2 | Chrome only (MV3) | Firefox, Safari | 65% market share, single manifest, ship faster |
| 3 | SSE streaming | Polling, WebSocket | Progressive UX, simpler than WS, works from popup/side panel |
| 4 | `create_task + Queue` over `asyncio.gather()` | `gather()`, `as_completed()` | Enables SSE partial results, per-crawler timeouts, graceful degradation |
| 5 | Local transformer + LLM fallback | LLM-only, lexicon-only | $0 primary path, high accuracy, resilient |
| 6 | Google OAuth | Email/password, Clerk, anonymous fingerprint | Zero friction in Chrome, stable user ID for rate limiting, free |
| 7 | Defer X/Twitter | Include at $100/mo, Nitter scraping | Blows budget 5x, low signal vs Reddit/YouTube for product reviews |
| 8 | Own Amazon scraping | Rainforest API, SerpAPI | Existing infrastructure, $0 marginal cost |
| 9 | Hetzner CX32 over Vercel serverless | Vercel, Railway, Fly.io | Stateful workloads, no cold starts, raw compute per euro, €9/mo |
| 10 | User rate cap 5-10/day | Unlimited, pay-per-use | Cost control and abuse prevention at MVP |
| 11 | SOLID crawler architecture (Strategy + Parser + Crawler) | Flat BaseCrawler | Swappable crawl backends (crawl4ai, scrapegraph), new platforms without modifying existing code |
| 12 | Single-server monolith | Split API + worker servers | YAGNI — €9 vs €18, one compose file, scaling wall is far past PMF |

---

## 4. Request Flow

```
Extension (Chrome MV3)
   │
   ├─ User lands on Amazon page → extension scrapes ASIN + product title
   │
   ├─ GET /api/v1/product/{asin}/stream
   │   Headers: Authorization: Bearer <google_jwt>
   │
   ▼
FastAPI
   │
   ├─ 1. Auth middleware: validate JWT → extract user_id
   ├─ 2. Rate limit check: Redis INCR user:{user_id}:daily → reject 429 if > limit
   │
   ├─ 3. Cache check:
   │     ├─ FRESH hit (TTL < 3hr)  → return cached result, close SSE
   │     ├─ STALE hit (3hr < TTL < 24hr) → return stale via SSE + background refresh
   │     └─ MISS → proceed to crawl
   │
   ├─ 4. Distributed lock: SET product:lock:{asin} NX EX 30
   │     └─ Lock exists? → subscribe to Redis pub/sub channel product:{asin}
   │        → receive result when first request completes
   │
   └─ 5. Lock acquired → create crawl tasks:
         │
         ├─ create_task(reddit_crawler)  → Queue.put() on complete
         ├─ create_task(youtube_crawler) → Queue.put() on complete
         └─ create_task(amazon_crawler)  → Queue.put() on complete
               │
               ▼
         SSE handler drains Queue:
           → event: {source: "reddit", status: "done", count: 23}
           → event: {source: "youtube", status: "done", count: 8}
           → event: {source: "amazon", status: "done", count: 142}
               │
               ▼
         Sentiment analysis (local model, single batch pass)
               │
               ▼
         Aggregate → compute verdict
               │
               ▼
         Write: Postgres (reviews + score) + Redis (cache with TTL)
               │
               ▼
         SSE final: {verdict: "BUY", confidence: 0.82, summary: "..."}
         Release lock. Close SSE.
```

### Key mechanisms:

- **Lock coalescing:** If 5 users look up the same ASIN simultaneously, only one crawl runs. Others subscribe via Redis pub/sub.
- **Three-tier cache:** Fresh (instant) → Stale (instant + background refresh) → Miss (full crawl).
- **Graceful timeout:** Each crawler has individual timeout. If Amazon fails, verdict renders from Reddit + YouTube.

---

## 5. Data Model

### Postgres Tables

```sql
── users ──────────────────────────────────
id              UUID PK DEFAULT gen_random_uuid()
google_id       TEXT UNIQUE NOT NULL
email           TEXT NOT NULL
display_name    TEXT
tier            TEXT DEFAULT 'free'        -- 'free' | 'admin' | 'premium'
daily_limit     INT DEFAULT 10
created_at      TIMESTAMPTZ DEFAULT now()
last_login_at   TIMESTAMPTZ

── products ───────────────────────────────
id              UUID PK DEFAULT gen_random_uuid()
asin            TEXT UNIQUE NOT NULL
title           TEXT NOT NULL
image_url       TEXT
category        TEXT
first_seen_at   TIMESTAMPTZ DEFAULT now()
last_crawled_at TIMESTAMPTZ

── reviews ────────────────────────────────
id              UUID PK DEFAULT gen_random_uuid()
product_id      UUID FK → products.id
source          TEXT NOT NULL               -- 'reddit' | 'youtube' | 'amazon'
source_id       TEXT NOT NULL               -- platform-specific ID
content         TEXT NOT NULL
author          TEXT
sentiment       FLOAT                       -- -1.0 to 1.0
sentiment_label TEXT                         -- 'positive' | 'negative' | 'neutral'
posted_at       TIMESTAMPTZ
crawled_at      TIMESTAMPTZ DEFAULT now()
UNIQUE(source, source_id)

── product_scores ─────────────────────────
id              UUID PK DEFAULT gen_random_uuid()
product_id      UUID FK → products.id UNIQUE
verdict         TEXT NOT NULL               -- 'BUY' | 'DONT_BUY' | 'MIXED'
confidence      FLOAT NOT NULL              -- 0.0 to 1.0
positive_pct    FLOAT
negative_pct    FLOAT
neutral_pct     FLOAT
total_reviews   INT
summary         TEXT
sources_json    JSONB                        -- per-source breakdown
computed_at     TIMESTAMPTZ DEFAULT now()
```

### Redis Keys

| Key Pattern | Type | TTL | Purpose |
|---|---|---|---|
| `user:{user_id}:daily` | INT (INCR) | Midnight reset | Rate limit counter |
| `product:{asin}:result` | JSON string | 3hr fresh / 24hr stale | Cached verdict + reviews |
| `product:lock:{asin}` | String (SET NX) | 30s | Distributed crawl lock |
| `product:{asin}:channel` | Pub/Sub | — | Lock coalescing |

---

## 6. Crawler Architecture (SOLID)

### Three-layer separation:

**Layer 1 — CrawlStrategy** (how to fetch raw data)

```python
class CrawlStrategy(Protocol):
    async def fetch(self, url: str, params: dict) -> RawResponse: ...

# Implementations:
class ApiStrategy:              # REST API calls (Reddit, YouTube)
class AiohttpScrapeStrategy:    # HTTP scraping with proxies (Amazon)
class Crawl4aiStrategy:         # crawl4ai drop-in
class ScrapegraphStrategy:      # scrapegraphai LLM-powered extraction
```

**Layer 2 — PlatformParser** (how to extract reviews from raw data)

```python
class PlatformParser(Protocol):
    def parse(self, raw: RawResponse) -> list[RawReview]: ...

# Implementations per platform:
class RedditJsonParser:
class YouTubeApiParser:
class AmazonHtmlParser:
```

**Layer 3 — PlatformCrawler** (coordinates strategy + parser)

```python
class PlatformCrawler:
    def __init__(self, source: str, strategy: CrawlStrategy,
                 parser: PlatformParser, timeout: float = 10.0): ...

    async def crawl(self, asin: str, title: str, queue: asyncio.Queue) -> None:
        try:
            raw = await asyncio.wait_for(
                self.strategy.fetch(...), timeout=self.timeout)
            reviews = self.parser.parse(raw)
            await queue.put(CrawlerResult(
                source=self.source, status="done", reviews=reviews))
        except asyncio.TimeoutError:
            await queue.put(CrawlerResult(
                source=self.source, status="timeout", reviews=[]))
        except Exception:
            await queue.put(CrawlerResult(
                source=self.source, status="error", reviews=[]))
```

### Per-platform configuration (MVP):

| Platform | Strategy | Parser | Timeout | Auth |
|---|---|---|---|---|
| Reddit | `ApiStrategy` | `RedditJsonParser` | 8s | OAuth2 client credentials |
| YouTube | `ApiStrategy` | `YouTubeApiParser` | 10s | API key |
| Amazon | `AiohttpScrapeStrategy` | `AmazonHtmlParser` | 12s | Proxy rotation |

### Extensibility:

- **New platform:** Write one parser class + one config entry.
- **Swap crawl backend:** Change strategy in config. Zero changes to parser or crawler.

---

## 7. Sentiment and Verdict Engine

### Sentiment service (strategy pattern):

```python
class SentimentProvider(Protocol):
    async def analyze(self, texts: list[str]) -> list[SentimentResult]: ...

class LocalTransformerProvider:   # Primary — CPU, ~2-4s/batch
class LlmApiProvider:             # Fallback — OpenAI/Anthropic, ~1-3s

class SentimentService:
    def __init__(self, primary: SentimentProvider,
                 fallback: SentimentProvider): ...
    # tries primary, falls back on exception
```

### Verdict computation:

```python
weights = {"amazon": 1.0, "reddit": 1.2, "youtube": 0.8}

if weighted_avg > 0.25 and positive_pct > 0.55:
    verdict = "BUY"
elif weighted_avg < -0.15 or negative_pct > 0.45:
    verdict = "DONT_BUY"
else:
    verdict = "MIXED"

confidence = abs(weighted_avg) * min(1.0, total_reviews / 20)
```

- Reddit weighted higher (1.2) — harder to fake than Amazon reviews.
- Minimum viable verdict: at least 5 reviews from at least 1 source.
- Summary: template-based for MVP, LLM-generated in v2.

---

## 8. Error Handling

| Failure | Response |
|---|---|
| Single crawler fails/times out | SSE error event for that source, verdict from remaining |
| All crawlers fail | SSE final: `{verdict: "UNAVAILABLE"}` |
| Sentiment model crash | Auto-fallback to LLM API |
| LLM fallback also fails | Return reviews without sentiment, verdict = `INSUFFICIENT_DATA` |
| Redis down | Skip cache, crawl fresh, don't cache |
| Postgres down | SSE still delivers verdict in-memory, persist fails silently |
| Duplicate concurrent requests | Lock coalescing via Redis pub/sub |
| Rate limit exceeded | 429 with `{remaining: 0, resets_at: timestamp}` |

**Core principle:** Always return something to the user. Never a blank screen or hung spinner.

---

## 9. Infrastructure

### Docker Compose on Hetzner CX32 (4 vCPU, 8GB, €9/mo)

| Service | Image | RAM Budget |
|---|---|---|
| Caddy | `caddy:2-alpine` | ~30MB |
| FastAPI | Custom (2 uvicorn workers) | ~400MB |
| Postgres 15 | `postgres:15-alpine` | ~500MB |
| Redis 7 | `redis:7-alpine` (512MB max) | ~512MB |
| Sentiment model | Loaded in FastAPI process | ~1.5GB |
| Prefect worker | Custom | ~200MB |
| OS + buffers | — | ~1GB |
| **Headroom** | — | **~3.8GB** |

### Project structure:

```
evident-backend/
├── apps/api/src/
│   ├── main.py
│   ├── core/         (config, database, redis, security)
│   ├── routers/      (auth, product, health)
│   ├── services/     (orchestrator, cache, rate_limiter, sentiment/)
│   ├── crawlers/     (base, factory, strategies/, platforms/)
│   └── models/       (user, product, review, product_score)
├── pipelines/flows/  (Prefect recrawl)
├── alembic/
├── docker-compose.yml
├── Dockerfile
├── Caddyfile
└── pyproject.toml
```

---

## 10. Testing Strategy

| Layer | Tool | Scope |
|---|---|---|
| Unit | pytest + pytest-asyncio | Parsers, verdict computation, rate limiter |
| Integration | pytest + httpx.AsyncClient | SSE flow (mocked crawlers), auth, cache paths |
| Crawler contract | pytest + respx/VCR.py | Recorded API responses, detect format changes |
| Load (pre-launch) | locust | 10 concurrent SSE streams on CX32 |

---

## 11. Cost Summary

| Item | Monthly Cost |
|---|---|
| Hetzner CX32 | €9 |
| Domain | ~€1 |
| Reddit API | Free |
| YouTube Data API | Free |
| Amazon crawling | $0 (own infra) |
| X/Twitter | Deferred |
| LLM fallback (occasional) | ~$1-2 |
| **Total** | **~€12/mo (~$13)** |
