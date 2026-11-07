import logging

from app.common.logging_config import setup_logging

logger = logging.getLogger(__name__ if __name__ != "__main__" else "app.main")

from app.db.session import close_database
from app.presentation.app import run
from app.presentation.main_window import ApplicationContainer

def main() -> None:
    setup_logging()
    logger.info("Football Management System started.")
    try:
        run(ApplicationContainer(), close_database)
    except Exception:
        logger.critical("Football Management System stopped after a fatal error.", exc_info=True)
        raise SystemExit(1) from None
    else:
        logger.info("Football Management System closed.")


if __name__ == "__main__":
    main()
