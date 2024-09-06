import os
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from sqlalchemy import create_engine

from database_queries import DatabaseQueries
from database_server_operations import QueryMetadata, QueryResults
from main import app
from scraper import Arxiv

client = TestClient(app)


# Fixture to mock the database queries
@pytest.fixture
def mock_db_queries():
    with patch("database_queries.DatabaseQueries") as MockDatabaseQueries:
        yield MockDatabaseQueries()


# Fixture to mock the get_all_queries_between_timestamps method
@pytest.fixture
def mock_get_all_queries_between_timestamps():
    with patch.object(
        DatabaseQueries, "get_all_queries_between_timestamps"
    ) as mock_get_all_queries_between_timestamps:
        yield mock_get_all_queries_between_timestamps


# Fixture to mock the create_query_results_array method
@pytest.fixture
def mock_create_query_results_array():
    with patch.object(
        DatabaseQueries, "create_query_results_array"
    ) as mock_create_query_results_array:
        yield mock_create_query_results_array


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
@pytest.fixture(autouse=True)
def mock_create_query_metadata_result():
    with patch.object(Arxiv, "create_query_metadata_result") as mock_create_metadata:
        yield mock_create_metadata


# Fixture to mock the parse_query_response_content method
@pytest.fixture
def mock_parse_query_response_content():
    with patch.object(Arxiv, "parse_query_response_content") as mock_parse:
        yield mock_parse


# Fixture to mock the check_and_compose_url method
@pytest.fixture(autouse=True)
def mock_check_and_compose_url():
    with patch.object(Arxiv, "check_and_compose_url") as mock_compose_url:
        yield mock_compose_url


# Fixture to mock the PDFGenerator class
@pytest.fixture
def mock_pdf_generator():
    with patch("helper_module.PDFGenerator.generate_pdf") as mock_pdf:
        yield mock_pdf


def test_scrape_arxiv(
    mock_requests_get,
    mock_db_engine,
    mock_parse_query_response_content,
    mock_create_query_metadata_result,
    mock_check_and_compose_url,
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
        mock_check_and_compose_url.return_value = True
        mock_create_query_metadata_result.return_value = (query_metadata, query_results)
        response = client.get(
            "/arxiv/?author=SampleAuthor&skip=0&max_results=8&sortBy=relevance&sortOrder=descending"
        )
        assert response.status_code == 200


def test_get_queries_as_pdf(
    mock_db_queries, mock_pdf_generator, mock_get_all_queries_between_timestamps
):
    columns = ["query", "timestamp", "status", "num_results"]
    results = [
        MagicMock(
            query="sample query",
            timestamp="2021-06-01T00:00:00",
            status=200,
            num_results="1",
        )
    ]

    mock_get_all_queries_between_timestamps.return_value = (columns, results)
    mock_pdf_generator.return_value = MagicMock()

    response = client.get(
        "/queries/?query_timestamp_start=2021-06-01T00:00:00&query_timestamp_end=2021-06-30T23:59:59"
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"


def test_get_queries_as_json(mock_get_all_queries_between_timestamps):
    columns = ["query", "timestamp", "status", "num_results"]
    results = [
        MagicMock(
            query="sample query",
            timestamp="2021-06-01T00:00:00",
            status=200,
            num_results="1",
        )
    ]

    mock_get_all_queries_between_timestamps.return_value = (columns, results)

    query_timestamp_start = "2021-06-01T00:00:00"
    query_timestamp_end = "2021-06-30T23:59:59"

    response = client.post(
        "/queries/",
        params={
            "query_timestamp_start": query_timestamp_start,
            "query_timestamp_end": query_timestamp_end,
        },
    )

    assert response.status_code == 200
    json_response = response.json()
    assert json_response == [
        {
            "query": "sample query",
            "timestamp": "2021-06-01T00:00:00",
            "status": 200,
            "num_results": 1,
        }
    ]


def test_get_query_results(mock_create_query_results_array):
    mock_results = [
        ("Author 1", "Sample Title", "Sample Journal"),
        ("Author 2", "Another Title", "Another Journal"),
    ]

    mock_create_query_results_array.return_value = mock_results

    with patch("database_server_operations.create_engine"):
        response = client.get("/results/?page=1&size=10")
        assert response.status_code == 200
        json_response = response.json()
        assert "result" in json_response
        assert json_response["result"] == [
            {
                "author": "Author 1",
                "title": "Sample Title",
                "journal": "Sample Journal",
            },
            {
                "author": "Author 2",
                "title": "Another Title",
                "journal": "Another Journal",
            },
        ]
