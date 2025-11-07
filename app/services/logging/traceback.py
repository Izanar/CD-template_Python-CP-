import sys
from io import StringIO
from typing import Any, TextIO

from rich.console import Console
from rich.traceback import Traceback
from structlog.processors import ExceptionRenderer
from structlog.tracebacks import ExceptionDictTransformer
from structlog.typing import EventDict, ExcInfo, WrappedLogger

dict_tracebacks = ExceptionRenderer()


class ExtendedExceptionRenderer:
    def __init__(self):
        self.dict_transformer = ExceptionDictTransformer()

    def __call__(self, logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
        exc_info = event_dict.pop("exc_info", None)
        if exc_info:
            exc_info = _figure_out_exc_info(exc_info)
            event_dict["exception"] = {
                "traceback": self.render_traceback(exc_info),
            }

        return event_dict

    def render_traceback(self, exc_info: ExcInfo) -> str:
        sio = StringIO()
        better_rich_traceback(sio=sio, exc_info=exc_info)
        return sio.getvalue()


def _figure_out_exc_info(v: Any) -> ExcInfo:
    """
    Depending on the Python version will try to do the smartest thing possible
    to transform *v* into an ``exc_info`` tuple.
    """
    if isinstance(v, BaseException):
        return v.__class__, v, v.__traceback__
    if isinstance(v, tuple):
        return v
    if v:
        return sys.exc_info()

    return v


def better_rich_traceback(sio: TextIO, exc_info: ExcInfo) -> None:
    """
    Pretty-print *exc_info* to *sio* using the *Rich* package.

    To be passed into `ConsoleRenderer`'s ``exception_formatter`` argument.

    Used by default if *Rich* is installed.

    .. versionadded:: 21.2
    """
    sio.write("\n")
    Console(file=sio, width=120, safe_box=False).print(
        Traceback.from_exception(
            *exc_info,
            show_locals=True,
            extra_lines=1,
            width=120,
        )
    )
