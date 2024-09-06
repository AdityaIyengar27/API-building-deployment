# ArXiv Scraper API

## Overview

This project is a demonstration of how to build and deploy a simple API that scrapes data from the arxiv.org API, stores the results in a PostgreSQL database, and provides endpoints to query and retrieve the stored data. The API has three main endpoints:

1. **`/arxiv`**: Scrapes the arxiv.org API and stores results in the PostgreSQL database.
2. **`/queries`**: Fetches queries from the PostgreSQL database based on query timestamps (Returns the results in a PDF file for GET requests, returns JSON for POST requests).
3. **`/results`**: Provides all stored query results in JSON format with pagination support.

## Tech Stack

- **Python**: Programming language used for the project.
- **FastAPI**: Framework used to build the API.
- **SQLAlchemy**: Object Relational Mapper (ORM) tool (Library) used to interact with the databases.
- **PostgreSQL**: Database used to store queries and results.
- **Docker**: Used to containerize the application and manage services.

## Setup and Installation

### Prerequisites

- Docker

**Ensure that Docker is installed on your system and running.**

### Build and Run the Application
Run the following command in a terminal: 

```bash
docker-compose up --build
```

This command will build the Docker images, start the services and run the application in the foreground. 
To run the application in the background, use the `-d` flag:

```bash
docker-compose up --build -d
```

### Accessing the API
Once the services are up and running, you can access the API at: [`http://0.0.0.0:8080`](http://0.0.0.0:8080)

## API Endpoints

### 1. `/arxiv/`

- **Description**: Scrapes the arxiv.org API and stores the results in the PostgreSQL database.
- **Method**: `GET`
- **Request Parameters**:
  - `author` (Optional): Author's name
  - `title` (Optional): Title of the paper
  - `journal` (Optional): Journal name
  - `max_query_results` (Optional): Maximum number of query results to return. Default is 8.
- **Response**: Response message with status code.

### 2. `/queries/`

- **Description**: Fetches queries from the PostgreSQL database based on query timestamps.
- **Method**: `GET` or `POST`
  - `GET`: Fetches queries and stores the results in a PDF file.
  - `POST`: Fetches queries and returns the results in JSON format.
- **Request Parameters**:
  - `query_timestamp_start` (required): Start timestamp in 'yyyy-MM-dd’T'HH:mm' format.
  - `query_timestamp_end` (Optional): End timestamp in 'yyyy-MM-dd’T'HH:mm' format. Default is current timestamp.
- **Response**: JSON object or a PDF file containing the queries.

### 3. `/results/`

- **Description**: Provides all stored query results in JSON format with pagination support.
- **Method**: `GET`
- **Request Parameters**:
  - `page` (Optional): Page number. Default is 1.
  - `items_per_page` (Optional): Number of items per page. Default is 10.
- **Response**: JSON object containing the query results.

## Project Structure
```
├── tests
    ├── test_main.py
    ├── test_database_queries.py
    ├── test_database_server_operations.py
    ├── test_scraper.py
├── Dockerfile
├── docker-compose.yml
├── .env
├── main.py
├── database_queries.py
├── database_server_operations.py
├── helper_module.py
├── scraper.py
└── README.md

```

## Database Schema

The database schema consists of two tables:
- **`query_metadata`**: Stores the query details.
  - `id`: Primary key - Unique identifier for the query, returned from arxiv.org API.
  - `query`: Query string used to fetch the results.
  - `num_results`: Number of results than can be fetched.
  - `max_results`: Maximum number of results to fetch.
  - `status`: Status of the query response from arxiv.org API.
  - `timestamp`: Timestamp of the query.
- **`query_results`**: Stores the query results.
  - `id`: Primary key - Incremental identifier for the query result.
  - `query_id`: Foreign key - Identifier of the query.
  - `author`: Author of the paper.
  - `title`: Title of the paper.
  - `journal`: Journal name.
  - `time_of_storage`: Timestamp of the query result storage.

## Additional/Useful Docker commands
To bring down the services, run the following command:

```bash
docker-compose down
```

To view the volumes associated with the services, run the following command:

```bash
docker volume ls
```

To remove the volumes associated with the database, run the following command:

```bash
docker volume rm mlops_problem_db
```

#### Note - This will remove all the data stored in the database.

## Running Tests
To run the tests separately, execute the following command:

```bash
docker-compose run test
```


## Important Notes
- Ensure that the PostgreSQL database is up and running before making any API requests.
- The API is containerized using Docker to simplify the deployment process.
- The API is designed to be simple and easy to use, with minimal dependencies

## Future Improvements
- Add validation for the datetime format in the query parameters.
- Improve validation for no results found in the database for the given query timestamps instead of returning an empty response.
- Convert the timestamp/datetime values to UTC before storing them in the database.
- Add support for different storage formats (e.g., CSV, Excel, etc.) for the query results
- Add validation for max number of pages from the results endpoint so that if we exceed the max number of pages (all the rows from query_results table), we return an error message.

## References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)
- [Docker Documentation](https://docs.docker.com/)
- [arXiv API Documentation](https://info.arxiv.org/help/api/user-manual.html)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/16/intro-whatis.html)