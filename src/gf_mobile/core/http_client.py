"""
Async HTTP helper.

Uses aiohttp when available; falls back to requests in a background thread.
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional, Tuple

try:
    import aiohttp  # type: ignore
except Exception:  # pragma: no cover
    aiohttp = None

try:
    import requests  # type: ignore
except Exception:  # pragma: no cover
    requests = None


async def request_json(
    method: str,
    url: str,
    json_body: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    data: Optional[Dict[str, Any]] = None,
    timeout: int = 10,
) -> Tuple[int, Optional[Dict[str, Any]], str]:
    """
    Make an HTTP request and return (status, json_data, text).

    json_data can be None if the response is not JSON.
    """
    if aiohttp is not None:
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                json=json_body,
                params=params,
                headers=headers,
                data=data,
                timeout=timeout,
            ) as resp:
                text = await resp.text()
                try:
                    data_json = await resp.json(content_type=None)
                except Exception:
                    data_json = None
                return resp.status, data_json, text

    if requests is None:
        raise RuntimeError("No HTTP client available (aiohttp/requests missing).")

    def _sync_request() -> Tuple[int, Optional[Dict[str, Any]], str]:
        response = requests.request(
            method,
            url,
            json=json_body,
            params=params,
            headers=headers,
            data=data,
            timeout=timeout,
        )
        text = response.text
        try:
            data_json = response.json()
        except Exception:
            data_json = None
        return response.status_code, data_json, text

    return await asyncio.to_thread(_sync_request)
