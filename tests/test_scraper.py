import os

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from sqlalchemy import create_engine

from scraper import Arxiv
from database_server_operations import QueryMetadata, QueryResults


# Fixture to mock the database queries
@pytest.fixture
def mock_db_queries():
    with patch("database_queries.DatabaseQueries") as MockDatabaseQueries:
        yield MockDatabaseQueries()


# Fixture to mock the requests.get method
@pytest.fixture
def mock_requests_get():
    with patch("requests.get") as mock_get:
        yield mock_get


# Fixture to mock the database engine
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


# Fixture to mock the environment variables
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


# Fixture to mock the create_query_metadata_result method
@pytest.fixture
def mock_create_query_metadata_result():
    with patch.object(Arxiv, "create_query_metadata_result") as mock_create_metadata:
        yield mock_create_metadata


# Fixture to mock the parse_query_response_content method
@pytest.fixture
def mock_parse_query_response_content():
    with patch.object(Arxiv, "parse_query_response_content") as mock_parse:
        yield mock_parse


def test_check_and_compose_url():
    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    assert arxiv.check_and_compose_url()
    assert (
        "search_query=au:test_author AND ti:test_title AND jr:test_journal" in arxiv.url
    )


def test_check_and_compose_url_no_params():
    arxiv = Arxiv(author=None, title=None, journal=None)
    assert not arxiv.check_and_compose_url()


def test_parse_query_response_content(mock_requests_get):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    parsed_content = arxiv.parse_query_response_content()
    assert parsed_content is not None


def test_create_query_metadata_result_no_results(mock_requests_get):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    arxiv.feed = {
        "feed": {
            "id": "http://arxiv.org/api/123",
            "title": "sample query",
            "opensearch_totalresults": "0",
        },
        "entries": [],
    }

    query_metadata, query_results = arxiv.create_query_metadata_result()
    print("Query Metadata:", query_metadata)  # Debug print
    print("Query Results:", query_results)  # Debug print
    assert query_metadata["id"] == "123"
    assert query_metadata["status"] == 200
    assert query_metadata["query"] == "sample query"
    assert query_metadata["num_results"] == "0"
    assert query_results == []


def test_create_query_metadata_result_query_results(mock_requests_get):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    arxiv.feed = {
        "feed": {
            "id": "http://arxiv.org/api/123",
            "title": "sample query",
            "opensearch_totalresults": "1",
        },
        "entries": [
            {
                "authors": [{"name": "Author 1"}],
                "title": "Sample Title",
                "arxiv_journal_ref": "Sample Journal",
            }
        ],
    }

    query_metadata, query_results = arxiv.create_query_metadata_result()
    assert query_metadata["id"] == "123"
    assert query_metadata["status"] == 200
    assert query_metadata["query"] == "sample query"
    assert query_metadata["num_results"] == "1"


def test_create_query_results_array(mock_requests_get):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    arxiv.feed = {
        "feed": {
            "id": "http://arxiv.org/api/123",
            "title": "sample query",
            "opensearch_totalresults": "1",
        },
        "entries": [
            {
                "authors": [{"name": "Author 1"}],
                "title": "Sample Title",
                "arxiv_journal_ref": "Sample Journal",
            }
        ],
    }

    query_metadata, query_results = arxiv.create_query_metadata_result()
    assert query_metadata["id"] == "123"
    assert query_metadata["status"] == 200
    assert query_metadata["query"] == "sample query"
    assert query_metadata["num_results"] == "1"
    assert len(query_results) == 1
    assert query_results[0]["query_id"] == "123"
    assert query_results[0]["author"] == "Author 1"
    assert query_results[0]["title"] == "Sample Title"
    assert query_results[0]["journal"] == "Sample Journal"


def test_query_arxiv_store_in_db_success(
    mock_db_queries,
    mock_requests_get,
    mock_db_engine,
    mock_parse_query_response_content,
    mock_create_query_metadata_result,
):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(
        author="test_author",
        title="test_title",
        journal="test_journal",
        max_query_results=8,
    )
    arxiv.response = mock_response
    mock_parse_query_response_content.return_value = {}

    query_metadata = {
        "id": "123",
        "status": 200,
        "query": "sample query",
        "num_results": "1",
        "max_results": 8,
        "timestamp": datetime.now(),
    }
    query_results = [
        {
            "id": 1,
            "query_id": "123",
            "author": "Author 1",
            "title": "Sample Title",
            "journal": "Sample Journal",
            "time_of_storage": datetime.now(),
        }
    ]

    with patch("database_server_operations.create_engine"):
        mock_create_query_metadata_result.return_value = (query_metadata, query_results)
        status_code = arxiv.query_arxiv_store_in_db()
        assert status_code == 200


def test_query_arxiv_store_in_db_no_results(
    mock_db_queries,
    mock_requests_get,
    mock_db_engine,
    mock_parse_query_response_content,
    mock_create_query_metadata_result,
):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    mock_parse_query_response_content.return_value = {}

    query_metadata = {
        "id": "123",
        "status": 200,
        "query": "sample query",
        "num_results": "0",
        "max_results": 8,
        "timestamp": datetime.now(),
    }
    query_results = []

    with patch("database_server_operations.create_engine"):
        mock_create_query_metadata_result.return_value = (query_metadata, query_results)
        status_code = arxiv.query_arxiv_store_in_db()
        assert status_code == 422


def test_query_arxiv_store_in_db_query_exists(
    mock_db_queries,
    mock_requests_get,
    mock_db_engine,
    mock_parse_query_response_content,
    mock_create_query_metadata_result,
):
    mock_response = MagicMock()
    mock_response.content = "mock_content"
    mock_response.status_code = 200
    mock_response.headers = {"Date": "Tue, 03 Jun 2021 19:56:14 GMT"}
    mock_requests_get.return_value = mock_response

    arxiv = Arxiv(author="test_author", title="test_title", journal="test_journal")
    arxiv.response = mock_response
    mock_parse_query_response_content.return_value = {}

    query_metadata = {
        "id": "123",
        "status": 200,
        "query": "sample query",
        "num_results": "1",
        "max_results": 8,
        "timestamp": datetime.now(),
    }
    query_results = [
        {
            "id": 1,
            "query_id": "123",
            "author": "Author 1",
            "title": "Sample Title",
            "journal": "Sample Journal",
            "time_of_storage": datetime.now(),
        }
    ]

    with patch("database_server_operations.create_engine"):
        mock_create_query_metadata_result.return_value = (query_metadata, query_results)
        status_code = arxiv.query_arxiv_store_in_db()
        assert status_code == 200
        # Try to insert the same query again
        status_code = arxiv.query_arxiv_store_in_db()
        assert status_code == 424
