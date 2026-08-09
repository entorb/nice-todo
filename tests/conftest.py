from pathlib import Path

import pytest

from src.database import Database


@pytest.fixture
def db(tmp_path: Path) -> Database:
    """Fresh SQLite database in a temp dir for each test."""
    database = Database(db_path=tmp_path / "test.db")
    database.init()
    return database
