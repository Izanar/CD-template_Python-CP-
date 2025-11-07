import logging
import sys
from datetime import datetime
from logging.config import dictConfig
from typing import Any, Dict

import orjson
import structlog
from pytz import utc
from starlette.requests import Request
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.services.logging.traceback import ExtendedExceptionRenderer, better_rich_traceback


def logs_dumper(value: dict[str, Any], default) -> str:
    return orjson.dumps(value, default=default).decode()


def setup_structlog(mode: str, level: str, show_sql: bool = False) -> Dict[str, Any]:
    log_level = logging.getLevelName(level.upper())
    additional_processors = []
    callsite_parameter = {
        structlog.processors.CallsiteParameter.MODULE,
        structlog.processors.CallsiteParameter.FUNC_NAME,
    }
    if mode == "generic":
        additional_processors.extend(
            [
                structlog.dev.ConsoleRenderer(exception_formatter=better_rich_traceback),
            ]
        )

    elif mode == "json":
        additional_processors.extend(
            [
                ExtendedExceptionRenderer(),
                structlog.processors.JSONRenderer(logs_dumper),
            ]
        )
        callsite_parameter.update(
            {
                structlog.processors.CallsiteParameter.PATHNAME,
                structlog.processors.CallsiteParameter.LINENO,
                structlog.processors.CallsiteParameter.THREAD,
                structlog.processors.CallsiteParameter.THREAD_NAME,
                structlog.processors.CallsiteParameter.PROCESS,
                structlog.processors.CallsiteParameter.PROCESS_NAME,
            }
        )
    else:
        raise RuntimeError(f"Logging mode {mode!r} is not supported")

    processors = [
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="ISO"),
        structlog.processors.CallsiteParameterAdder(callsite_parameter),
        structlog.contextvars.merge_contextvars,
        RemoveFieldsFilter("_record"),
        *additional_processors,
    ]

    structlog.stdlib.ProcessorFormatter(processors=processors)

    logger_propagate = {
        "handlers": ["stream"],
        "level": log_level,
        "propagate": True,
    }
    logger_no_propagate = logger_propagate | {"propagate": False}

    loggers = {
        "": logger_propagate,
        "celery.multi_agent": logger_no_propagate,
        "uvicorn.access": logger_no_propagate,
        "uvicorn.error": logger_no_propagate,
        "uvicorn.main": logger_no_propagate,
        "uvicorn.lifespan": logger_no_propagate,
    }
    if show_sql:
        # Is the same as echo=True in SQLAlchemy,
        # but we don't want to use echo because it duplicates messages in the logs
        loggers["sqlalchemy.engine"] = logger_no_propagate

    if log_level <= logging.INFO:
        # Celery logs are too verbose in DEBUG mode, so we set them to INFO
        loggers["celery"] = logger_no_propagate | {"level": logging.INFO}
        loggers["amqp"] = logger_no_propagate | {"level": logging.INFO}
        loggers["kombu"] = logger_no_propagate | {"level": logging.INFO}

    dict_logging = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "structlog": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processors": processors,
            }
        },
        "handlers": {
            "stream": {
                "level": log_level,
                "formatter": "structlog",
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stderr",
            },
        },
        "loggers": loggers,
    }
    dictConfig(dict_logging)

    structlog.configure(
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        processors=[
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        cache_logger_on_first_use=True,
    )
    return dict_logging


class RemoveFieldsFilter:
    def __init__(self, *names: str):
        self.names = names

    def __call__(self, logger, log_method, event_dict):
        for name in self.names:
            if name in event_dict:
                del event_dict[name]
        return event_dict


def ensure_key_from_state(key: str, request: Request, ctx: dict[str, Any]):
    if value := getattr(request.state, key, None):
        ctx[key] = value


async def add_logging_context(request: Request, call_next):
    ctx = {
        "http": {
            "method": request.method,
            "url": str(request.url.path),
            "client_ip": request.client.host,
            "started": datetime.now(utc),
        }
    }
    clear_contextvars()
    bind_contextvars(**ctx)

    try:
        result = await call_next(request)
    finally:
        ensure_key_from_state(key="cashier_id", request=request, ctx=ctx)
        ensure_key_from_state(key="cash_register_id", request=request, ctx=ctx)
        ensure_key_from_state(key="device_id", request=request, ctx=ctx)
        ensure_key_from_state(key="client_info", request=request, ctx=ctx)
        bind_contextvars(**ctx)

    return result


def loki_logger() -> logging.Logger:
    _loki_logger: logging.Logger = logging.getLogger("loki_logger")
    _loki_logger.setLevel(logging.INFO)
    _loki_logger.propagate = False
    _loki_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)

    handler.setFormatter(logging.Formatter("%(message)s"))

    _loki_logger.addHandler(handler)

    return _loki_logger
