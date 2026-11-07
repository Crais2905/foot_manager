import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from app.application.exceptions import (
    ApplicationError, ApplicationValidationError, DatabaseError, EntityConflictError, EntityNotFoundError,
)
from app.domain.errors import DomainConflictError
from app.infrastructure.unit_of_work import UnitOfWork

P = ParamSpec("P")
T = TypeVar("T")


def logged_operation(operation: Callable[P, Awaitable[T]]) -> Callable[P, Awaitable[T]]:
    logger = logging.getLogger(operation.__module__)
    name = operation.__qualname__

    @wraps(operation)
    async def run(*args: P.args, **kwargs: P.kwargs) -> T:
        logger.info("%s started.", name)
        try:
            result = await operation(*args, **kwargs)
        except DatabaseError:
            logger.error("%s failed due to a database error.", name)
            raise
        except ApplicationError:
            logger.warning("%s was rejected.", name, exc_info=True)
            raise
        except Exception:
            logger.exception("%s failed unexpectedly.", name)
            raise
        logger.info("%s completed.", name)
        return result

    return run


def validated(operation: Callable[P, T], *args: P.args, **kwargs: P.kwargs) -> T:
    try:
        return operation(*args, **kwargs)
    except DomainConflictError as error:
        raise EntityConflictError(str(error)) from error
    except (TypeError, ValueError) as error:
        raise ApplicationValidationError(str(error)) from error


def require(entity: T | None, label: str, entity_id: int) -> T:
    if entity is None:
        raise EntityNotFoundError(f"{label} (ID {entity_id}) не знайдено.")
    return entity


class Service:
    def __init__(self, uow_factory: Callable[[], UnitOfWork] = UnitOfWork) -> None:
        self._uow = uow_factory
