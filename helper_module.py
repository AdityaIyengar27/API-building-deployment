import io
from datetime import datetime
from textwrap import wrap
from typing import List

from fastapi import HTTPException, FastAPI, Query
from pydantic import BaseModel
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from database_queries import DatabaseQueries

app = FastAPI()


class CheckDate:
    """
    Class to check date format and return date in 'YYYY-MM-DDTHH:MM:SS' format
    """

    @staticmethod
    def return_date_format(date: datetime):
        """
        Function to return date in 'YYYY-MM-DDTHH:MM:SS' format
        :param date: Datetime object
        :return: date in 'YYYY-MM-DDTHH:MM:SS' format
        """

        try:
            return date.strftime("%Y-%m-%dT%H:%M:%S")
        except ValueError:
            raise UnicornException(
                status_code=500,
                msg="Timestamps must be in the format 'YYYY-MM-DDTHH:MM:SS'",
            )


class QueryBetweenTimestamps(BaseModel):
    """
    Pydantic model for query between timestamps
    """

    query: str
    timestamp: datetime
    status: int
    num_results: int


class QueryResultList(BaseModel):
    """
    Pydantic model for query results
    """

    author: str
    title: str | None
    journal: str | None


class Pagination(BaseModel):
    """
    Pydantic model for pagination
    """

    items_per_page: int
    page: int


class PagedResponseSchema:
    """Response schema for any paged API."""

    @staticmethod
    def pagination_params(
        page: int = Query(ge=1, required=False, default=1),
        items_per_page: int = Query(ge=1, required=False, default=10, le=100),
    ):
        return Pagination(page=page, items_per_page=items_per_page)


class ResultList(BaseModel):
    """
    Pydantic model for query results
    """

    result: List[QueryResultList]


class DBSession:
    """
    Class to handle database session
    """

    # database session creation
    @staticmethod
    def get_db_session():
        db_queries = DatabaseQueries()
        return db_queries.session


class PDFGenerator:
    """
    Class to generate PDF output
    """

    @staticmethod
    def generate_pdf(columns: List[str], results: List[List[str]]) -> io.BytesIO:
        pdf_output = io.BytesIO()
        c = canvas.Canvas(pdf_output, pagesize=letter)
        width, height = letter

        # Define starting coordinates
        x = 40
        y = height - 50
        bottom_margin = 50

        # Define column widths and row height
        column_widths = (width - 80) / len(columns)  # Width of each column
        default_row_height = 20  # Height of each row

        # Function to draw header
        def draw_header():
            nonlocal y
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.line(x, y, x, y - default_row_height)  # Vertical line on the left
            for i, column in enumerate(columns):
                c.drawString(
                    x + i * column_widths + 5, y - 13, column
                )  # Column header text
                if not i == len(columns) - 1:
                    c.line(
                        x + i * column_widths, y, x + (i + 1) * column_widths, y
                    )  # Horizontal line above header
                    c.line(
                        x + i * column_widths,
                        y - default_row_height,
                        x + (i + 1) * column_widths,
                        y - default_row_height,
                    )  # Horizontal line below header
                    c.line(
                        x + (i + 1) * column_widths,
                        y,
                        x + (i + 1) * column_widths,
                        y - default_row_height,
                    )  # Vertical line on the right
                else:
                    # Adjust the last column width to fit the page
                    c.line(
                        x + i * column_widths, y, (x + (i + 1) * column_widths) - 40, y
                    )  # Horizontal line above header
                    c.line(
                        x + i * column_widths,
                        y - default_row_height,
                        (x + (i + 1) * column_widths) - 40,
                        y - default_row_height,
                    )  # Horizontal line below header
                    c.line(
                        (x + (i + 1) * column_widths) - 40,
                        y,
                        (x + (i + 1) * column_widths) - 40,
                        y - default_row_height,
                    )  # Vertical line

            # Move to the next line
            y -= default_row_height

        # Function to draw row
        def draw_row(row):
            nonlocal y
            max_wrap_lines = 1  # Track the maximum number of lines wrapped in a cell for the current row
            wrapped_texts = []

            # Wrap text in each cell
            for i, value in enumerate(row):
                wrapped_text = wrap(
                    str(value), width=int((column_widths / 6) - 5)
                )  # Wrap text based on the column width
                wrapped_texts.append(wrapped_text)
                max_wrap_lines = max(max_wrap_lines, len(wrapped_text))

            # Adjust row height based on the max wrapped lines
            row_height = 15 * max_wrap_lines

            for i, wrapped_text in enumerate(wrapped_texts):
                for j, line in enumerate(wrapped_text):
                    c.drawString(x + i * column_widths + 5, y - 13 - j * 15, line)

                if not i == len(columns) - 1:
                    c.line(
                        x + i * column_widths, y, x + (i + 1) * column_widths, y
                    )  # Horizontal line above row
                    c.line(
                        x + i * column_widths,
                        y - row_height,
                        x + (i + 1) * column_widths,
                        y - row_height,
                    )  # Horizontal line below row
                    c.line(
                        x + (i + 1) * column_widths,
                        y,
                        x + (i + 1) * column_widths,
                        y - row_height,
                    )  # Vertical line on the right
                else:
                    c.line(
                        x + i * column_widths, y, (x + (i + 1) * column_widths) - 40, y
                    )  # Horizontal line above row
                    c.line(
                        x + i * column_widths,
                        y - row_height,
                        (x + (i + 1) * column_widths) - 40,
                        y - row_height,
                    )  # Horizontal line below row
                    c.line(
                        (x + (i + 1) * column_widths) - 40,
                        y,
                        (x + (i + 1) * column_widths) - 40,
                        y - row_height,
                    )  # Vertical line on the right
            c.line(x, y, x, y - row_height)  # Vertical line on the left
            y -= row_height  # Move to the next line

        # Draw the table header
        draw_header()

        # Draw the table rows with lines and page breaks
        for row in results:
            # Check if the next row would go below the bottom margin
            if y - default_row_height < bottom_margin:
                c.showPage()
                y = height - 50  # Reset y to the top of the new page
                draw_header()  # Draw the header on the new page

            draw_row(row)  # Draw the row

        c.save()
        pdf_output.seek(0)
        return pdf_output


class UnicornException(Exception):
    """
    Custom exception class for handling exceptions
    """

    def __init__(self, status_code: int, msg: str):
        self.status_code = status_code
        self.msg = msg


class Response:
    """
    Class to handle response codes
    """

    @staticmethod
    def response_code(status_code: int):
        """
        Function to handle response codes
        :param status_code:
        :return: None
        """
        match status_code:
            case 200:
                return "Query from arXiv API successful and stored in the database"
            case 420:
                raise UnicornException(
                    status_code=status_code,
                    msg="At least one of author, title, or journal must be provided.",
                )
            case 421:
                raise UnicornException(
                    status_code=status_code,
                    msg="Arxiv API is not responding. Please try again later",
                )
            case 422:
                raise UnicornException(
                    status_code=status_code,
                    msg="No results from this query that was made to arXiv API. Please check the input parameters",
                )
            case 423:
                raise UnicornException(
                    status_code=status_code,
                    msg="Failed to store query and results in the database",
                )
            case 424:
                raise UnicornException(
                    status_code=status_code,
                    msg="Query already exists. Please retrieve it from the database",
                )
            case 425:
                raise UnicornException(
                    status_code=status_code,
                    msg="Query start timestamp cannot be in the future",
                )
            case 426:
                raise UnicornException(
                    status_code=status_code,
                    msg="Query end timestamp cannot be before the start timestamp",
                )
            case 427:
                raise UnicornException(
                    status_code=status_code,
                    msg="Timestamps must be in the format 'YYYY-MM-DDTHH:MM:SS'",
                )
            case 428:
                raise UnicornException(
                    status_code=status_code,
                    msg="No Query results found in the database for the given timestamps",
                )
            case _:
                raise HTTPException(status_code=400, detail="Unknown error occurred")
