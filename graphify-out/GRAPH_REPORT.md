# Graph Report - evident-backend  (2026-05-15)

## Corpus Check
- 69 files · ~11,021 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 10 nodes · 11 edges · 3 communities (1 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d447498a`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]

## God Nodes (most connected - your core abstractions)
1. `auth_google()` - 4 edges
2. `AuthResponse` - 3 edges
3. `lifespan()` - 2 edges
4. `AuthRequest` - 2 edges
5. `create_access_token()` - 2 edges
6. `Application lifespan: startup and shutdown hooks.` - 1 edges
7. `Exchange Google ID token for a session JWT.          Verifies the Google token,` - 1 edges

## Surprising Connections (you probably didn't know these)
- `AuthResponse` --inherits--> `BaseModel`  [EXTRACTED]
  routers/auth.py →   _Bridges community 2 → community 0_

## Communities (3 total, 2 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.6
Nodes (4): auth_google(), AuthResponse, create_access_token(), Exchange Google ID token for a session JWT.          Verifies the Google token,

## Knowledge Gaps
- **2 isolated node(s):** `Application lifespan: startup and shutdown hooks.`, `Exchange Google ID token for a session JWT.          Verifies the Google token,`
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `AuthResponse` connect `Community 0` to `Community 2`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **What connects `Application lifespan: startup and shutdown hooks.`, `Exchange Google ID token for a session JWT.          Verifies the Google token,` to the rest of the system?**
  _2 weakly-connected nodes found - possible documentation gaps or missing edges._