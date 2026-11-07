import asyncio
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


async def until(predicate, app=None, timeout=5):
    async with asyncio.timeout(timeout):
        while not predicate():
            if app is not None:
                app.processEvents()
            await asyncio.sleep(0.01)


def press(parent, text):
    from PySide6.QtWidgets import QPushButton

    button = next(button for button in parent.findChildren(QPushButton) if button.text() == text)
    assert button.isEnabled()
    button.click()


async def dialog_of(kind, app):
    def visible_dialog():
        active = app.activeModalWidget()
        if active is not None:
            return active if isinstance(active, kind) else None
        return next((widget for widget in app.topLevelWidgets()
                     if isinstance(widget, kind) and widget.isVisible()), None)

    await until(lambda: visible_dialog() is not None, app)
    return visible_dialog()
