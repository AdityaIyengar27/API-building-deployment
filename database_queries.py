from sqlalchemy import insert, asc, select

from database_server_operations import (
    DatabaseServerOperations,
    QueryMetadata,
    QueryResults,
)
from datetime import datetime


class DatabaseQueries:
    """
    In this class, we create a database connection and session
    In addition, we perform various database query operations such as inserting data into the table,
    getting query metadata, checking if query ID exists, getting all queries between timestamps,
    creating a list of query results, and committing the session
    """

    def __init__(self):
        self.db_operation = DatabaseServerOperations()
        self.engine = self.db_operation.create_engine()
        self.session = self.db_operation.create_session(engine=self.engine)

    def insert_into_table(
        self, table: [QueryMetadata, QueryResults], data: [dict, list]
    ) -> None:
        """
        In this function, we insert data into the table
        :param table: QueryMetadata or QueryResults
        :param data: Data to insert
        :return: None
        """
        self.session.execute(insert(table=table), data)

    def get_query_metadata(self, query_id: str) -> QueryMetadata:
        """
        In this function, we get the query metadata
        :param query_id: ID of the query
        :return: QueryMetadata object
        """
        return self.session.query(QueryMetadata).filter(QueryMetadata.id == query_id)

    def check_if_query_id_exists(self, query_id: str) -> bool:
        """
        In this function, we check if the query ID exists
        :param query_id: ID of the query
        :return: Boolean value indicating if the query ID exists
        """
        return self.get_query_metadata(query_id=query_id).first() is not None

    def get_all_queries_between_timestamps(
        self, start_timestamp: datetime, end_timestamp: datetime
    ) -> ([str], [QueryMetadata]):
        """
        In this function, we get all queries between the timestamps
        :param start_timestamp: Start timestamp - format: yyyy-MM-dd’T’HH:mm:ss
        :param end_timestamp: End timestamp - format: yyyy-MM-dd’T’HH:mm:ss
        :return: List of columns and list of QueryMetadata objects
        """
        # Create a query to get all queries between the timestamps
        query = (
            self.session.query(
                QueryMetadata.query,
                QueryMetadata.timestamp,
                QueryMetadata.status,
                QueryMetadata.num_results,
            )
            .filter(QueryMetadata.timestamp >= start_timestamp)
            .filter(QueryMetadata.timestamp <= end_timestamp)
        )
        result = query.all()

        # Get column names from the query result
        columns = [col["name"] for col in query.column_descriptions]

        return columns, result

    def create_query_results_array(self, pagination):
        """
        In this function, we create a list of query results
        :param pagination: Pagination parameters for the query results
        :return: List of query results, count of the total number of rows in the table
        """
        # Create a query to get the query results with pagination
        query = (
            select(QueryResults.author, QueryResults.title, QueryResults.journal)
            .limit(pagination.items_per_page)
            .offset(
                pagination.page - 1
                if pagination.page
                == 1  # If we are requesting first page, we go to item 0 (when we start counting rows)
                else (pagination.page - 1) * pagination.items_per_page
                # Calculate the offset based on the page number and items per page.
                # The counting is 0-based as the index is zero based. So, we need to subtract 1 from the page number.
            )
            .order_by(asc(QueryResults.time_of_storage))
        )

        # Execute the query to get the results
        result = self.session.execute(query).all()

        return result

    def commit_session(self) -> None:
        """
        In this function, we commit the session and close it
        :return: None
        """
        self.session.commit()
        self.session.close()
