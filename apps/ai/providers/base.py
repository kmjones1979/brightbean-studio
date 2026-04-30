"""Shared HTTP base class — handles timeout, single retry on 5xx/network."""

from __future__ import annotations

import logging
import time

import httpx

from apps.ai.providers.types import ProviderError

logger = logging.getLogger(__name__)


class HTTPProviderBase:
    """Base class with timeout + single-retry-on-5xx semantics for HTTP-based providers."""

    name: str = ""
    default_timeout: float = 30.0

    def __init__(self, *, base_url: str, api_key: str, extra_headers: dict | None = None):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.extra_headers = extra_headers or {}

    def _post_with_retry(self, path: str, json_body: dict, *, timeout: float | None = None) -> tuple[dict, int, str]:
        """POST `json_body` to `self.base_url + path`. Returns (json, status, request_id).
        Retries once on 5xx or network error. No retry on 4xx.
        """
        timeout = timeout or self.default_timeout
        url = f"{self.base_url}{path}"

        for attempt in (0, 1):
            start = time.monotonic()
            try:
                resp = httpx.post(
                    url,
                    json=json_body,
                    timeout=timeout,
                    headers=self._auth_headers(),
                )
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                if attempt == 0:
                    logger.warning("Provider %s network error, retrying once: %s", self.name, exc)
                    continue
                raise ProviderError(f"{self.name} network error: {exc}") from exc

            elapsed_ms = int((time.monotonic() - start) * 1000)

            if resp.status_code >= 500 and attempt == 0:
                logger.warning(
                    "Provider %s returned %s, retrying once. body: %s",
                    self.name,
                    resp.status_code,
                    resp.text[:200],
                )
                continue

            if resp.status_code >= 400:
                raise ProviderError(f"{self.name} HTTP {resp.status_code}: {resp.text[:300]}")

            data = resp.json()
            request_id = resp.headers.get("x-request-id", "") or resp.headers.get("request-id", "")
            return data, elapsed_ms, request_id

        raise ProviderError(f"{self.name} unreachable after retry")

    def _auth_headers(self) -> dict[str, str]:
        raise NotImplementedError
