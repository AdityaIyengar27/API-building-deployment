import os
import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine

from database_server_operations import (
    DatabaseServerOperations,
    QueryMetadata,
    QueryResults,
)


# Fixture to mock environment variables
@pytest.fixture(autouse=True)
def mock_env_vars():
    with patch.dict(
        os.environ,
        {
            "DB_USER": "test_user",
            "DB_PASSWORD": "test_password",
            "DB_NAME": "test_db",
            "DB_PORT": "5432",
        },
    ):
        yield


# Fixture to mock database engine
@pytest.fixture(autouse=True)
def mock_db_engine():
    with patch(
        "database_server_operations.DatabaseServerOperations.create_engine"
    ) as mock_create_engine:
        mock_engine = create_engine("sqlite:///:memory:")
        mock_create_engine.return_value = mock_engine
        yield mock_engine


def test_make_db_url():
    with patch("database_server_operations.create_engine"):
        db_operations = DatabaseServerOperations()
        expected_url = "postgresql+psycopg2://test_user:test_password@db:5432/test_db"
        assert db_operations.make_db_url() == expected_url


def test_create_engine():
    with patch("database_server_operations.create_engine"):
        db_operations = DatabaseServerOperations()
        engine = db_operations.create_engine()
        assert engine.url == create_engine("sqlite:///:memory:").url


def test_create_session():
    with patch("database_server_operations.create_engine"):
        db_operations = DatabaseServerOperations()
        mock_engine = MagicMock()
        session = db_operations.create_session(mock_engine)
        assert session.bind == mock_engine


def test_create_table_if_not_exists(mock_db_engine):
    with patch.object(
        QueryMetadata.__table__, "create"
    ) as mock_create_metadata, patch.object(
        QueryResults.__table__, "create"
    ) as mock_create_results:

        DatabaseServerOperations()
        # As create_table_if_not_exists is called in the __init__ method of DatabaseServerOperations
        # we need to create an instance of the class to call the method and not explicitly call the method

        mock_create_metadata.assert_called_once_with(
            bind=mock_db_engine, checkfirst=True
        )
        mock_create_results.assert_called_once_with(
            bind=mock_db_engine, checkfirst=True
        )
