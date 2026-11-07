class ApplicationError(Exception):
    """An expected error that a caller can present to the user."""


class EntityNotFoundError(ApplicationError):
    pass


class EntityConflictError(ApplicationError):
    pass


class ApplicationValidationError(ApplicationError):
    pass

class DatabaseError(ApplicationError):
    """Database operation failed without a user-correctable constraint conflict."""
