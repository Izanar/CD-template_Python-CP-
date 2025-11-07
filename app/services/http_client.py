import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(
        self, base_url: str, api_key: str, timeout: float = 10.0, max_retries: int = 3, retry_delay: float = 1.0
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    async def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Api-Key": self.api_key, "Content-Type": "application/json"}

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries} for {url}")

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e.response.text}")

            except Exception as e:
                last_exception = e
                logger.warning(f"Request failed on attempt {attempt + 1}/{self.max_retries} for {url}: {e!s}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"All {self.max_retries} attempts failed for {url}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to API after {self.max_retries} attempts: {last_exception!s}"
        )

    async def put(self, endpoint: str, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self.base_url}{endpoint}"
        headers = {"Api-Key": self.api_key, "Content-Type": "application/json"}

        last_exception = None

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.put(url, headers=headers, json=data)
                    response.raise_for_status()
                    return response.json()

            except httpx.TimeoutException as e:
                last_exception = e
                logger.warning(f"Timeout on attempt {attempt + 1}/{self.max_retries} for {url}")

            except httpx.HTTPStatusError as e:
                logger.error(f"HTTP error {e.response.status_code} for {url}: {e.response.text}")
                raise HTTPException(status_code=e.response.status_code, detail=f"API error: {e.response.text}")

            except Exception as e:
                last_exception = e
                logger.warning(f"Request failed on attempt {attempt + 1}/{self.max_retries} for {url}: {e!s}")

            if attempt < self.max_retries - 1:
                await asyncio.sleep(self.retry_delay * (attempt + 1))

        logger.error(f"All {self.max_retries} attempts failed for {url}")
        raise HTTPException(
            status_code=500, detail=f"Failed to connect to API after {self.max_retries} attempts: {last_exception!s}"
        )
