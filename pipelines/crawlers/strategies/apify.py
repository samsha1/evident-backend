"""
Apify Actor runner — async, resilient, shared across all platforms.

Uses the run-sync-get-dataset-items endpoint for fast actors (<5 min),
and falls back to async start → poll → fetch for slower ones.
"""

from __future__ import annotations

import asyncio
import logging
import aiohttp
from pipelines.crawlers.core.base import CrawlStrategy

logger = logging.getLogger(__name__)

# Apify REST base URL
_APIFY_BASE = "https://api.apify.com/v2"

# Per-request timeout for the synchronous run endpoint (Apify max = 300 s)
_SYNC_TIMEOUT_SECS = 270

# How often to poll when using the async flow (seconds)
_POLL_INTERVAL = 5
# Maximum total wait when polling (seconds)
_POLL_TIMEOUT = 300


class ApifyStrategy(CrawlStrategy):
    """
    Base CrawlStrategy that runs an Apify Actor and returns dataset items
    as a JSON string.

    Subclasses must implement `build_input(query)` to return the actor's
    run-input dict for a given search query.

    The `actor_id` class attribute identifies which Actor to run
    (format: ``username/actor-name`` or ``username~actor-name``).
    """

    actor_id: str  # Override in each subclass

    def __init__(self, api_token: str, use_async: bool = False):
        """
        Args:
            api_token: Apify API token.
            use_async: If True, use async start + poll instead of sync endpoint.
                       Set True for actors that routinely run >5 minutes.
        """
        self.api_token = api_token
        self.use_async = use_async

    def build_input(self, query: str) -> dict:
        """Return actor run-input for the given query. Override per platform."""
        raise NotImplementedError

    # ------------------------------------------------------------------
    # CrawlStrategy protocol
    # ------------------------------------------------------------------

    async def fetch(self, query: str, **kwargs) -> str:
        """Run the actor and return dataset items as a JSON string."""
        run_input = self.build_input(query)
        if self.use_async:
            return await self._run_async_flow(run_input)
        return await self._run_sync_flow(run_input)

    # ------------------------------------------------------------------
    # Sync flow  (fast actors, single HTTP call)
    # ------------------------------------------------------------------

    async def _run_sync_flow(self, run_input: dict) -> str:
        import json

        actor_slug = self.actor_id.replace("/", "~")
        url = (
            f"{_APIFY_BASE}/acts/{actor_slug}"
            f"/run-sync-get-dataset-items?token={self.api_token}"
        )
        timeout = aiohttp.ClientTimeout(total=_SYNC_TIMEOUT_SECS)

        logger.info(f"[Apify] Starting sync run for actor: {self.actor_id}")
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(url, json=run_input) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    logger.info(
                        f"[Apify] Sync run complete for {self.actor_id}: "
                        f"{len(items)} items"
                    )
                    return json.dumps(items)

                text = await resp.text()
                logger.error(
                    f"[Apify] Sync run failed for {self.actor_id}: "
                    f"HTTP {resp.status} — {text[:300]}"
                )
                return json.dumps([])

    # ------------------------------------------------------------------
    # Async flow  (longer-running actors)
    # ------------------------------------------------------------------

    async def _run_async_flow(self, run_input: dict) -> str:
        import json

        actor_slug = self.actor_id.replace("/", "~")
        start_url = f"{_APIFY_BASE}/acts/{actor_slug}/runs?token={self.api_token}"

        async with aiohttp.ClientSession() as session:
            # 1. Start the run
            logger.info(f"[Apify] Starting async run for actor: {self.actor_id}")
            async with session.post(start_url, json={"input": run_input}) as resp:
                if resp.status not in (200, 201):
                    text = await resp.text()
                    logger.error(f"[Apify] Failed to start run: HTTP {resp.status} — {text[:300]}")
                    return json.dumps([])
                run_data = await resp.json()

            run_id: str = run_data["data"]["id"]
            dataset_id: str = run_data["data"]["defaultDatasetId"]
            logger.info(f"[Apify] Run started: {run_id} (dataset: {dataset_id})")

            # 2. Poll until terminal state
            status_url = f"{_APIFY_BASE}/actor-runs/{run_id}?token={self.api_token}"
            elapsed = 0
            while elapsed < _POLL_TIMEOUT:
                await asyncio.sleep(_POLL_INTERVAL)
                elapsed += _POLL_INTERVAL

                async with session.get(status_url) as resp:
                    if resp.status != 200:
                        continue
                    run_info = await resp.json()

                status = run_info["data"]["status"]
                logger.debug(f"[Apify] Run {run_id} status: {status}")

                if status == "SUCCEEDED":
                    break
                if status in ("FAILED", "ABORTED", "TIMED-OUT"):
                    logger.error(f"[Apify] Run {run_id} terminal state: {status}")
                    return json.dumps([])
            else:
                logger.error(f"[Apify] Polling timed out for run {run_id}")
                return json.dumps([])

            # 3. Fetch dataset items
            items_url = (
                f"{_APIFY_BASE}/datasets/{dataset_id}/items"
                f"?token={self.api_token}&format=json"
            )
            async with session.get(items_url) as resp:
                if resp.status == 200:
                    items = await resp.json()
                    logger.info(
                        f"[Apify] Fetched {len(items)} items from dataset {dataset_id}"
                    )
                    return json.dumps(items)

                text = await resp.text()
                logger.error(f"[Apify] Failed to fetch dataset: HTTP {resp.status} — {text[:300]}")
                return json.dumps([])
