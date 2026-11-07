import logging
import sys
import traceback
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

DEFAULT_LOG_DIR = Path("logs")


class DiagnosticFormatter(logging.Formatter):
    """Preserve stack locations and exception types without logging driver payloads."""

    def formatException(
        self, info: tuple[type[BaseException], BaseException, TracebackType | None] | tuple[None, None, None],
    ) -> str:
        lines: list[str] = []
        seen: set[int] = set()

        def append(error: BaseException, stack: TracebackType | None) -> None:
            if id(error) in seen:
                return
            seen.add(id(error))
            cause = error.__cause__
            if cause is None and not error.__suppress_context__:
                cause = error.__context__
            if cause is not None:
                append(cause, cause.__traceback__)
                lines.append("The preceding exception led to:")
            if stack is not None:
                lines.append("Traceback (most recent call last):")
                for frame, line in traceback.walk_tb(stack):
                    lines.append(f'  File "{frame.f_code.co_filename}", line {line}, in {frame.f_code.co_name}')
            lines.append(f"{type(error).__module__}.{type(error).__qualname__}")
            if isinstance(error, BaseExceptionGroup):
                for nested in error.exceptions:
                    append(nested, nested.__traceback__)

        if info[1] is not None:
            append(info[1], info[2])
        return "\n".join(lines)


class ApplicationFileHandler(RotatingFileHandler):
    def handleError(self, record: logging.LogRecord) -> None:
        # The console handler still receives the record. Never dump LogRecord arguments.
        if not getattr(self, "_warned", False):
            self._warned = True
            if sys.stderr is not None:
                sys.stderr.write("Football Manager: запис журналу у файл недоступний.\n")


def setup_logging(
    log_dir: Path = DEFAULT_LOG_DIR, *, level: int = logging.INFO,
    max_bytes: int = 5 * 1024 * 1024,
) -> None:
    logger = logging.getLogger("app")
    logger.setLevel(level)
    logger.propagate = False
    for handler in logger.handlers[:]:
        if getattr(handler, "_football_manager", False):
            logger.removeHandler(handler)
            handler.close()

    formatter = DiagnosticFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    )

    def attach(handler: logging.Handler) -> None:
        setattr(handler, "_football_manager", True)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    attach(logging.StreamHandler())
    try:
        log_dir.mkdir(parents=True, exist_ok=True)
        attach(ApplicationFileHandler(
            log_dir / "application.log", maxBytes=max_bytes, backupCount=5, encoding="utf-8",
        ))
    except OSError:
        logger.warning("File logging is unavailable. Continuing with console logging.", exc_info=True)
