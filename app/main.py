import asyncio
import contextlib
import json
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.responses import ORJSONResponse
from prometheus_fastapi_instrumentator import PrometheusFastApiInstrumentator
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from . import SUMMARY
from .api.routes.admin.admin import admin_router
from .api.routes.admin.geo import admin_geo_router
from .api.routes.admin.keitaro import admin_keitaro_router
from .api.routes.admin.primitives import (
    admin_celebrity_router,
    admin_funnel_router,
    admin_language_router,
    admin_site_name_router,
)
from .api.routes.admin.tasks.designer_tasks import admin_designer_tasks_router
from .api.routes.admin.tasks.web_master_tasks import admin_web_master_tasks_router
from .api.routes.admin.teams.designers_team import admin_designers_team_router
from .api.routes.admin.teams.media_buyers_team import admin_media_buyers_team_router
from .api.routes.admin.teams.web_masters_team import admin_web_masters_team_router
from .api.routes.auth import auth_router
from .api.routes.creatives import creatives_router
from .api.routes.designers.designer_team import designer_team_router
from .api.routes.designers.designers import designer_router
from .api.routes.designers.lead_designer import lead_designer_router
from .api.routes.external import external_api_router
from .api.routes.internal import nuke_router
from .api.routes.keitaro import router as keitaro_router
from .api.routes.media_buyers.assistant import assistant_router
from .api.routes.media_buyers.lead_media_buyers import lead_media_buyer_router
from .api.routes.media_buyers.media_buyer_team import media_buyer_team_router
from .api.routes.media_buyers.tasks.designer_tasks import buyer_designer_tasks_router
from .api.routes.media_buyers.tasks.web_master_tasks import buyer_web_master_tasks_router
from .api.routes.media_file import media_files
from .api.routes.statistics import statistics
from .api.routes.task_history import task_history_router
from .api.routes.telegram import telegram_router
from .api.routes.web_masters.lead_web_master import lead_web_master_router
from .api.routes.web_masters.web_master import web_master_router
from .api.routes.web_masters.web_master_team import web_master_team_router
from .config.config import ConfigDTO, create_application_config
from .core.aws import setup_s3_bucket
from .database.session import setup_database
from .dependecies.stub import (
    AppConfigStub,
    DatabaseRepositoryStub,
    DatabaseStub,
    InjectContextManager,
    InjectS3Resource,
    InjectStatic,
    S3BucketStub,
    SessionStub,
)
from .repository.database.base import DatabaseRepository
from .services.logging.logging_config import add_logging_context, loki_logger, setup_structlog
from .services.telegram import TelegramService

logger = structlog.get_logger()


def create_app(
    configure_logging: bool = True,
    application_config: ConfigDTO | None = None,
    telegram_service: TelegramService | None = None,
) -> FastAPI:
    if not application_config:
        application_config = create_application_config()

    if configure_logging:
        setup_structlog(
            mode=application_config.logging.mode,
            level=application_config.logging.level,
        )

    database = setup_database(config=application_config)
    database_repository = DatabaseRepository.create(session_maker=database.async_session_maker)

    if telegram_service is None:
        telegram_service = TelegramService(telegram_repo=database_repository.telegram)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        bot_task = asyncio.create_task(telegram_service.start_polling())
        try:
            yield
        finally:
            bot_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await bot_task

    application = FastAPI(
        title="Helper Back Core API",
        version="1",
        summary=SUMMARY,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
        middleware=[
            Middleware(
                BaseHTTPMiddleware,
                dispatch=add_logging_context,
            ),
            Middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            ),
        ],
    )

    application.dependency_overrides[AppConfigStub] = InjectStatic(application_config)
    database = setup_database(config=application_config)
    database_repository = DatabaseRepository.create(session_maker=database.async_session_maker)

    application.dependency_overrides[SessionStub] = InjectContextManager(database.async_session_maker)
    application.dependency_overrides[DatabaseStub] = InjectStatic(database)
    s3_session = setup_s3_bucket(config=application_config)
    application.dependency_overrides[S3BucketStub] = InjectS3Resource(
        session=s3_session, bucket_name=application_config.s3_config.bucket_name
    )
    application.dependency_overrides[DatabaseRepositoryStub] = InjectStatic(database_repository)

    application.include_router(auth_router)

    application.include_router(admin_router)
    application.include_router(admin_keitaro_router)
    application.include_router(admin_media_buyers_team_router)
    application.include_router(admin_web_masters_team_router)
    application.include_router(admin_designers_team_router)
    application.include_router(admin_designer_tasks_router)
    application.include_router(admin_web_master_tasks_router)

    application.include_router(media_buyer_team_router)
    application.include_router(lead_media_buyer_router)
    application.include_router(assistant_router)
    application.include_router(buyer_designer_tasks_router)
    application.include_router(buyer_web_master_tasks_router)

    application.include_router(web_master_team_router)
    application.include_router(lead_web_master_router)
    application.include_router(web_master_router)

    application.include_router(designer_team_router)
    application.include_router(lead_designer_router)
    application.include_router(designer_router)

    application.include_router(media_files)
    application.include_router(creatives_router)
    application.include_router(external_api_router)
    application.include_router(keitaro_router)
    application.include_router(task_history_router)
    application.include_router(statistics)
    application.include_router(telegram_router)
    application.include_router(admin_geo_router)

    application.include_router(admin_celebrity_router)
    application.include_router(admin_funnel_router)
    application.include_router(admin_language_router)
    application.include_router(admin_site_name_router)

    application.include_router(nuke_router)

    PrometheusFastApiInstrumentator(should_group_status_codes=False).instrument(application).expose(
        application, endpoint="/metrics"
    )

    return application


app = create_app()


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Response:
    _body = await request.body()
    response = await call_next(request)

    _response_body = b""
    async for chunk in response.body_iterator:
        _response_body += chunk
    try:
        parsed_response = json.loads(_response_body)
    except Exception:
        parsed_response = _response_body.decode("utf-8", errors="ignore") if _response_body else None

    try:
        body = json.loads(_body)
    except Exception:
        body = _body.decode("utf-8", errors="ignore") if _body else None

    log_data = {
        "type": "request",
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "query_params": dict(request.query_params),
        "body": body,
    }

    if 400 <= response.status_code < 600:
        log_data["response"] = parsed_response

    loki_logger().info(json.dumps(log_data))

    return Response(
        content=_response_body,
        status_code=response.status_code,
        headers=dict(response.headers),
        media_type=response.media_type,
    )
