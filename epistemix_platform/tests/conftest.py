"""
Shared test fixtures for database-related tests.
"""

import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

from epistemix_platform.repositories.database import Base


@pytest.fixture(scope="function")
def db_session(tmp_path_factory):
    """
    Create a test database session using tmp_path_factory for concurrent test safety.

    This fixture creates a unique temporary SQLite database for each test,
    ensuring that concurrent test runs don't interfere with each other.
    """
    tmp_dir = tmp_path_factory.mktemp("db")
    db_path = os.path.join(tmp_dir, "test.sqlite")

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    Session = scoped_session(sessionmaker(bind=engine))
    session = Session()

    yield session

    session.close()
    Session.remove()
