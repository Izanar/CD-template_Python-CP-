from pydantic_settings import BaseSettings


class KeitaroSettings(BaseSettings):
    timeout: float = 10.0
    max_retries: int = 3
    retry_delay: float = 1.0
    campaigns_limit: int = 1000


settings = KeitaroSettings()
