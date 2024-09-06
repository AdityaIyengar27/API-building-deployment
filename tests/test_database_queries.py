from datetime import datetime
import pytest
from unittest.mock import patch

from sqlalchemy import create_engine

from database_queries import DatabaseQueries, QueryMetadata, QueryResults
from helper_module import PagedResponseSchema


# Fixture to mock database engine
@pytest.fixture(autouse=True)
def mock_db_engine():
    with patch(
            "database_server_operations.DatabaseServerOperations.create_engine"
    ) as mock_create_engine:
        mock_engine = create_engine("sqlite:///:memory:")
        mock_create_engine.return_value = mock_engine
        # Create tables in the mock database
        QueryMetadata.__table__.create(bind=mock_engine, checkfirst=True)
        QueryResults.__table__.create(bind=mock_engine, checkfirst=True)
        yield mock_engine


def test_insert_into_table():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        data = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, data)
        data = db_queries.get_query_metadata(query_id="123").first()
        assert data.id == "123"
        assert data.query == "sample query"
        assert data.timestamp == timestamp


def test_get_query_metadata():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        data = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, data)
        data = db_queries.get_query_metadata(query_id="123").first()
        assert data.id == "123"


def test_check_if_query_id_exists_true():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        data = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, data)
        assert db_queries.check_if_query_id_exists(query_id="123") == True


def test_check_if_query_id_exists_false():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        data = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, data)
        assert db_queries.check_if_query_id_exists(query_id="234") == False


def test_get_all_queries_between_timestamps():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        data = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, data)
        columns, data = db_queries.get_all_queries_between_timestamps(
            start_timestamp=timestamp, end_timestamp=datetime.now()
        )
        assert len(columns) == 4
        assert columns[0] == "query"
        assert len(data) == 1


def test_create_query_results_array():
    timestamp = datetime.now()
    with patch("database_server_operations.create_engine"):
        db_queries = DatabaseQueries()
        query_metadata = {"id": "123", "query": "sample query", "timestamp": timestamp}
        db_queries.insert_into_table(QueryMetadata, query_metadata)
        query_results = {
            "query_id": "123",
            "query": "sample query",
            "author": "author",
            "title": "title",
            "journal": "journal",
            "time_of_storage": timestamp,
        }
        db_queries.insert_into_table(QueryResults, query_results)
        pagination = PagedResponseSchema.pagination_params(page=1, items_per_page=10)
        result = db_queries.create_query_results_array(pagination)
        assert len(result) == 1
        assert result[0][0] == "author"
        assert result[0][1] == "title"
        assert result[0][2] == "journal"
