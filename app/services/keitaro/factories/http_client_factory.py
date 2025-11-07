from typing import Dict

from ...http_client import HttpClient
from ..settings import settings


class KeitaroHttpClientFactory:
    @staticmethod
    def create(keitaro_config: Dict[str, str]) -> HttpClient:
        return HttpClient(
            base_url=keitaro_config["base_url"],
            api_key=keitaro_config["api_key"],
            timeout=settings.timeout,
            max_retries=settings.max_retries,
            retry_delay=settings.retry_delay,
        )
