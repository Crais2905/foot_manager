import logging
from socket import gaierror

from sqlalchemy.exc import DBAPIError, IntegrityError, TimeoutError as PoolTimeoutError

from app.application.exceptions import (
    ApplicationError, ApplicationValidationError, DatabaseError, EntityConflictError,
)

logger = logging.getLogger(__name__)
DATABASE_FAILURES = (DBAPIError, PoolTimeoutError, ConnectionError, TimeoutError, gaierror)

_CONSTRAINT_MESSAGES = {
    "uq_championships_name": "Чемпіонат із такою назвою, країною та сезоном уже існує.",
    "uq_championship_participations_championship_id": "Це місце вже зайняте іншою командою.",
    "uq_championship_participations_team_id": "Команда вже бере участь у цьому чемпіонаті.",
    "uq_squad_players_squad_id": "Цей номер футболки вже використовується у складі.",
    "pk_squad_players": "Цей гравець уже є у складі.",
}


def translate_database_error(error: BaseException) -> ApplicationError | None:
    original = error.orig if isinstance(error, DBAPIError) else error
    sqlstate = getattr(original, "sqlstate", None)
    driver_error = getattr(original, "__cause__", None)
    constraint = getattr(driver_error, "constraint_name", "") or ""
    if isinstance(error, IntegrityError):
        if sqlstate == "23505":
            return EntityConflictError(_CONSTRAINT_MESSAGES.get(constraint, "Такий запис уже існує."))
        if sqlstate == "23503":
            return EntityConflictError("Операція суперечить зв’язкам між записами.")
        if sqlstate in {"23502", "23514"}:
            return ApplicationValidationError("Перевірте обов’язкові поля та допустимі значення.")
    if sqlstate in {"22001", "22003"}:
        return ApplicationValidationError("Одне з полів перевищує допустимий розмір.")
    if isinstance(error, DATABASE_FAILURES) or (
        isinstance(sqlstate, str) and type(error).__module__.startswith("asyncpg.")
    ):
        return DatabaseError()
    return None


def log_database_error(error: BaseException, translated: ApplicationError) -> None:
    original = error.orig if isinstance(error, DBAPIError) else error
    state = getattr(original, "sqlstate", None)
    sqlstate = state if isinstance(state, str) and len(state) == 5 and state.isalnum() else "unknown"
    logger.log(
        logging.ERROR if isinstance(translated, DatabaseError) else logging.WARNING,
        "Database operation failed (%s, SQLSTATE=%s).", type(translated).__name__, sqlstate,
        exc_info=(type(error), error, error.__traceback__),
    )
