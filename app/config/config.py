import sys
from ipaddress import IPv4Address
from pathlib import Path
from typing import Literal, TypeAlias

import orjson
import structlog
from orjson import JSONDecodeError
from pydantic import BaseModel, Field, HttpUrl, ValidationError, conint

logger = structlog.get_logger()

LogLevelType: TypeAlias = Literal[
    "CRITICAL",
    "FATAL",
    "ERROR",
    "WARNING",
    "WARN",
    "INFO",
    "DEBUG",
    "NOTSET",
]

DEFAULT_CONFIG_PATH = [
    Path.cwd(),
    Path.home() / ".helper_core",
]
DEFAULT_CONFIG_FILENAME = "config.json"


class LoggingConfig(BaseModel):
    mode: Literal["generic", "json"] = Field("generic", description="Режим логування")
    level: LogLevelType = Field("DEBUG", description="Рівень логування")


class WebServerConfig(BaseModel):
    host: IPv4Address
    port: conint(gt=0)
    docs: bool = False
    ssl: bool = False


class ProviderConfig(BaseModel):
    url: HttpUrl
    base_timeout: float = 10
    online_receipt_timeout: float = 4
    online_report_timeout: float = 6
    fetch_timeout: float = 0.75
    ssl_verify: bool = True
    trust_env: bool = True


class TokenConfig(BaseModel):
    secret_key: str
    algorithm: str
    expire_minutes: int = 300
    refresh_expire_days: int = 7


class S3BucketConfig(BaseModel):
    bucket_name: str
    access_key: str
    secret_key: str
    user: str
    region: str


class TransactionWorkerConfig(BaseModel):
    cash_registers_per_worker: int = 3
    worker_per_process: int = 2


class PostgresConfigDTO(BaseModel):
    dsn: str
    alembic: str | None = None
    pool_size: int = 20
    pool_max_overflow: int = 20
    pool_recycle: int = 60
    pool_timeout: int = 3
    connection_timeout: int = 5

    echo: bool = False


class TelegramConfig(BaseModel):
    token: str
    link: HttpUrl


class NotificationsConfig(BaseModel):
    url: HttpUrl
    api_key: str


class ExternalAPIConfig(BaseModel):
    api_key: str


class ConfigDTO(BaseModel):
    provider: ProviderConfig
    web_server: WebServerConfig
    postgres: PostgresConfigDTO
    jwt_token: TokenConfig
    s3_config: S3BucketConfig
    telegram: TelegramConfig
    notifications: NotificationsConfig
    external_api: ExternalAPIConfig
    logging: LoggingConfig = LoggingConfig()
    transaction_worker: TransactionWorkerConfig = TransactionWorkerConfig()


def resolve_config_file(raw_path: str | None = None) -> Path:
    if raw_path:
        config_path = Path(raw_path) / DEFAULT_CONFIG_FILENAME
        if config_path.exists():
            return config_path
    logger.debug("The path was not passed explicitly. Try to find in expected places...")
    for path in DEFAULT_CONFIG_PATH:
        config_path = path / DEFAULT_CONFIG_FILENAME
        if config_path.exists():
            return config_path
    logger.critical("Config file not found. Application startup failed")
    sys.exit(2)


def create_application_config(raw_path: str | None = None) -> ConfigDTO:
    config_path = resolve_config_file(raw_path=raw_path)
    try:
        config_data = orjson.loads(config_path.read_bytes())
        return ConfigDTO(**config_data)
    except OSError:
        sys.exit(2)
    except (JSONDecodeError, ValidationError):
        logger.exception("Config file has content errors. Parsing file impossible. Application startup failed")
        sys.exit(2)
