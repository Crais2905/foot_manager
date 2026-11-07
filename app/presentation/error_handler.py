import logging

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox, QWidget

from app.application.exceptions import (
    ApplicationError, ApplicationValidationError, DatabaseError, EntityConflictError, EntityNotFoundError,
)

logger = logging.getLogger(__name__)


class ErrorDialog(QMessageBox):
    def __init__(self, message: str, parent: QWidget) -> None:
        super().__init__(parent)
        self.setWindowTitle("Не вдалося виконати операцію")
        self.setIcon(QMessageBox.Icon.Critical)
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setText(message)
        self.setStandardButtons(QMessageBox.StandardButton.Close)
        self.button(QMessageBox.StandardButton.Close).setText("Закрити")
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)


class ErrorHandler:
    @staticmethod
    def get_user_message(error: Exception) -> str:
        if isinstance(error, DatabaseError):
            return "База даних недоступна або не виконала запит. Спробуйте ще раз."
        if isinstance(error, EntityNotFoundError):
            return str(error) or "Запитаний об’єкт не знайдено."
        if isinstance(error, EntityConflictError):
            return str(error) or "Операцію неможливо виконати через конфлікт даних."
        if isinstance(error, ApplicationValidationError):
            return str(error) or "Перевірте правильність введених даних."
        return "Сталася неочікувана помилка. Спробуйте ще раз."

    @classmethod
    def report(cls, error: Exception, parent: QWidget) -> str:
        message = cls.get_user_message(error)
        if isinstance(error, DatabaseError) or not isinstance(error, ApplicationError):
            logger.error(
                "GUI operation failed (%s).", type(error).__name__,
                exc_info=(type(error), error, error.__traceback__),
            )
            ErrorDialog(message, parent).open()
        else:
            logger.info("GUI operation was rejected (%s).", type(error).__name__)
        return message
