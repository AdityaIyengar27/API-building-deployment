from datetime import datetime
from typing import Optional, List, Annotated, Union

from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import StreamingResponse
from requests import Request
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from scraper import Arxiv

from database_queries import DatabaseQueries
from helper_module import (
    QueryBetweenTimestamps,
    PDFGenerator,
    Pagination,
    ResultList,
    PagedResponseSchema,
    DBSession,
    UnicornException,
    Response,
    CheckDate, QueryResultList,
)

app = FastAPI()


@app.exception_handler(UnicornException)
async def unicorn_exception_handler(
    request: Request, exc: UnicornException
) -> JSONResponse:
    """
    Exception handler for UnicornException
    :param request: request object
    :param exc: exception object
    :return: JSONResponse object with status code and message
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.msg,
    )


@app.get("/arxiv/", summary="Scrape arXiv API and store in the database")
async def scrape_arxiv(
    author: str | None = None,
    title: str | None = None,
    journal: str | None = None,
    max_query_results: int = 8,
):
    """
    Function to scrape arXiv API and store in the database
    - **author**: Author name
    - **title**: Title of the paper
    - **journal**: Journal name
    - **max_query_results**: Maximum number of query results. Default value is 8. \n

    This returns a response code indicating the status of the operation
    """
    # Create an Arxiv object
    arxiv_object = Arxiv(
        author=author,
        title=title,
        journal=journal,
        max_query_results=max_query_results,
    )
    # Check and compose the URL
    successful = arxiv_object.check_and_compose_url()
    if successful:
        # Query the arXiv API and store in the database
        status_code = arxiv_object.query_arxiv_store_in_db()
        return Response.response_code(status_code)
    else:
        # If at least one of author, title, or journal is not provided
        return Response.response_code(420)


@app.get("/queries/", summary="Get queries between timestamps as PDF")
async def get_queries_as_pdf(
    query_timestamp_start: datetime,
    query_timestamp_end: Optional[datetime] | None = None,
) -> StreamingResponse:
    """
    Function to get queries as a PDF
    - **query_timestamp_start**: Query start timestamp ’yyyy-MM-dd’T’HH:mm:ss’ (24 hrs. format)
    - **query_timestamp_end**: Query end timestamp ’yyyy-MM-dd’T’HH:mm:ss’ (24 hrs. format) \n

    This returns StreamingResponse containing the PDF
    """

    # Check if query_timestamp_start is in the future
    if query_timestamp_start > datetime.now():
        return Response.response_code(425)

    # Check if query_timestamp_end is before query_timestamp_start
    if query_timestamp_end is not None and query_timestamp_end < query_timestamp_start:
        return Response.response_code(426)

    # If query_timestamp_end is not provided, set it to the current timestamp
    if query_timestamp_end is None:
        query_timestamp_end = CheckDate.return_date_format(datetime.now())

    # Create a DatabaseQueries object
    db_queries = DatabaseQueries()

    try:
        # Get all queries between the timestamps with columns
        columns, results = db_queries.get_all_queries_between_timestamps(
            start_timestamp=CheckDate.return_date_format(query_timestamp_start),
            end_timestamp=query_timestamp_end,
        )

        # If no results are found
        if len(results) == 0:
            raise HTTPException(
                status_code=428,
                detail="No Query results found in the database for the given timestamps",
            )

        # Generate PDF output
        pdf_output = PDFGenerator.generate_pdf(columns=columns, results=results)

        # Return the PDF as a StreamingResponse
        return StreamingResponse(
            pdf_output,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=queries.pdf"},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_queries.engine.dispose()


@app.post(
    "/queries/",
    response_model=List[QueryBetweenTimestamps],
    summary="Get queries between timestamps as JSON",
)
async def get_queries_as_json(
    query_timestamp_start: datetime,
    query_timestamp_end: Optional[datetime] | None = None,
):
    """
    Function to get queries as JSON
    - **query_timestamp_start**: Query start timestamp ’yyyy-MM-dd’T’HH:mm:ss’ (24 hrs. format)
    - **query_timestamp_end**: Query end timestamp ’yyyy-MM-dd’T’HH:mm:ss’ (24 hrs. format) \n

    This returns a list of Dictionary objects containing query information in this format:
    {
        "query": "Query string",
        "timestamp": "Timestamp",
        "status": "Status",
        "num_results": "Number of results"
    }
    """

    # Check if query_timestamp_start is in the future
    if query_timestamp_start > datetime.now():
        return Response.response_code(425)

    # Check if query_timestamp_end is before query_timestamp_start
    if query_timestamp_end is not None and query_timestamp_end < query_timestamp_start:
        return Response.response_code(426)

    # If query_timestamp_end is not provided, set it to the current timestamp
    if query_timestamp_end is None:
        query_timestamp_end = CheckDate.return_date_format(datetime.now())

    # Create a DatabaseQueries object
    db_queries = DatabaseQueries()

    try:
        # Get all queries between the timestamps with columns
        columns, results = db_queries.get_all_queries_between_timestamps(
            start_timestamp=CheckDate.return_date_format(query_timestamp_start),
            end_timestamp=query_timestamp_end,
        )

        # If no results are found
        if len(results) == 0:
            raise HTTPException(
                status_code=428,
                detail="No Query results found in the database for the given timestamps",
            )

        # Create a list of QueryBetweenTimestamps objects
        query_list = [
            {
                "query": result.query,
                "timestamp": result.timestamp,
                "status": result.status,
                "num_results": result.num_results,
            }
            for result in results
        ]
        return query_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db_queries.engine.dispose()


@app.get("/results/", response_model=List[QueryResultList], summary="Get query results as JSON")
async def get_query_results(
    pagination: Annotated[Pagination, Depends(PagedResponseSchema.pagination_params)],
    db_session: Session = Depends(DBSession.get_db_session),
):
    """
    Function to get query results
    - **db_session**: Database session
    - **pagination**: Pagination parameters for the query results \n
    This returns a list of Dictionary objects containing query results in this format:

    {
        "author": "Author name",
        "title": "Title of the paper",
        "journal": "Journal name"
    }
    """

    try:
        with db_session:

            # Create a DatabaseQueries object
            """
            As db_session is part of DatabaseQueries object, can we use the same object 
            to call create_query_results_array method? --> No.
            
            But can we instead pass DatabaseQueries object to the function? Something to be improved??
            
            A little incosistency in the code as in get_queries_as_json
            we use a vairable to store results and then return that variable,
            but in this method we directly return the results??
            Not actually as the response model is ResultList and that contains an object result
            """
            db_queries = DatabaseQueries()
            results = db_queries.create_query_results_array(pagination)
            return {
                "result": [
                    # As result is a tuple, we need to access the elements by index
                    {
                        "author": result[0],
                        "title": result[1],
                        "journal": result[2],
                    }
                    for result in results
                ],
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
