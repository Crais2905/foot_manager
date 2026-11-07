import logging
import re

import pytest
from sqlalchemy.exc import IntegrityError

from app.application.exceptions import DatabaseError, EntityConflictError
from app.common.logging_config import setup_logging
from app.infrastructure.database_errors import translate_database_error


@pytest.fixture
def app_logger():
    logger = logging.getLogger("app")
    previous_level, previous_propagate = logger.level, logger.propagate
    yield logging.getLogger("app.test")
    for handler in logger.handlers[:]:
        if getattr(handler, "_football_manager", False):
            logger.removeHandler(handler)
            handler.close()
    logger.setLevel(previous_level)
    logger.propagate = previous_propagate


def test_log_reopens_in_append_mode_and_omits_secret_exception_text(tmp_path, app_logger, capsys):
    setup_logging(tmp_path)
    app_logger.info("Started.")
    setup_logging(tmp_path)
    app_logger.debug("Below configured threshold.")
    try:
        raise RuntimeError("postgresql://admin:TOPSECRET@localhost/football")
    except RuntimeError:
        app_logger.exception("Operation failed.")

    log = (tmp_path / "application.log").read_text(encoding="utf-8")
    assert re.search(r"\d{4}-\d\d-\d\d \d\d:\d\d:\d\d \| INFO \| app.test \| Started\.", log)
    assert log.count("Started.") == 1
    assert "Traceback (most recent call last)" in log and "RuntimeError" in log
    assert "Below configured threshold" not in log
    assert "TOPSECRET" not in log + capsys.readouterr().err


def test_rotates_five_backups_and_keeps_console_when_file_unavailable(tmp_path, app_logger, capsys):
    setup_logging(tmp_path, max_bytes=128)
    for index in range(16):
        app_logger.warning("Rotation record %s", index)
    assert {file.name for file in tmp_path.iterdir()} == {
        "application.log", *(f"application.log.{n}" for n in range(1, 6))
    }
    occupied = tmp_path / "occupied"
    occupied.write_text("already a file", encoding="utf-8")
    setup_logging(occupied)
    app_logger.info("Console remains active.")
    console = capsys.readouterr().err
    assert "File logging is unavailable" in console and "Console remains active." in console


def test_known_database_conflict_and_connection_errors_keep_distinct_types():
    class DriverConflict(Exception):
        sqlstate = "23505"

    cause = RuntimeError()
    cause.constraint_name = "uq_squad_players_squad_id"
    driver = DriverConflict("private database data")
    driver.__cause__ = cause
    conflict = translate_database_error(IntegrityError("private SQL", {}, driver))
    assert isinstance(conflict, EntityConflictError) and "номер" in str(conflict)
    assert isinstance(translate_database_error(ConnectionRefusedError()), DatabaseError)
    assert translate_database_error(ValueError()) is None
