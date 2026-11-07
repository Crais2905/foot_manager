import asyncio
from collections.abc import Awaitable, Callable
from importlib.resources import files
import sys

from PySide6.QtWidgets import QApplication
from qasync import QEventLoop

from app.presentation.error_handler import ErrorHandler
from app.presentation.main_window import ApplicationContainer, MainWindow


async def run_window(
    services: ApplicationContainer, cleanup: Callable[[], Awaitable[None]],
) -> None:
    window = MainWindow(services)
    closed = asyncio.Event()
    window.closed.connect(closed.set)
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()

    def handle_background_error(_loop: asyncio.AbstractEventLoop, context: dict) -> None:
        error = context.get("exception")
        if isinstance(error, Exception):
            ErrorHandler.report(error, window)
        else:
            ErrorHandler.report(RuntimeError("Unexpected event loop failure."), window)

    loop.set_exception_handler(handle_background_error)
    try:
        window.show()
        window.select_page(0)
        await closed.wait()
    finally:
        try:
            await window.runner.drain()
            await cleanup()
        finally:
            loop.set_exception_handler(previous_handler)


def run(services: ApplicationContainer, cleanup: Callable[[], Awaitable[None]]) -> None:
    qt = QApplication(sys.argv)
    qt.setApplicationName("Football Management System")
    qt.setStyle("Fusion")
    qt.setQuitOnLastWindowClosed(False)
    qt.setStyleSheet(files("app.presentation").joinpath("style.qss").read_text(encoding="utf-8-sig"))
    loop = QEventLoop(qt)
    asyncio.set_event_loop(loop)
    try:
        with loop:
            loop.run_until_complete(run_window(services, cleanup))
    finally:
        asyncio.set_event_loop(None)
