from datetime import datetime

import feedparser
import requests

from database_server_operations import (
    QueryMetadata,
    QueryResults,
)

from database_queries import DatabaseQueries


class Arxiv:
    """
    This class searches arxiv.org for the given author, title, and journal
    Also, it stores the query metadata and results in the database
    """

    def __init__(
        self,
        author: [str, None],
        title: [str, None],
        journal: [str, None],
        max_query_results: int = 8,
    ):
        """
        :param author: Author of a paper
        :param title: Title of a paper
        :param journal: Journal of a paper
        :param max_query_results: Maximum number of results to return
        """
        self.author = author
        self.title = title
        self.journal = journal
        self.max_query_results = max_query_results
        self.response = None
        self.feed = None
        self.url = None

    def check_and_compose_url(self) -> bool:
        """
        In this function, we check if at least one of the following is provided: author, title, or journal.
        We then compose the URL for the arxiv.org API
        :return: Boolean value indicating if the URL was successfully composed
        """
        search_params = []
        # Append the appropriate search parameters to the list
        if self.author:
            search_params.append(f"au:{self.author}")
        if self.title:
            search_params.append(f"ti:{self.title}")
        if self.journal:
            search_params.append(f"jr:{self.journal}")

        # Ensure at least one parameter is provided
        if not search_params:
            return False

        # Join the search parameters with '+' and return the full URL
        search_query = " AND ".join(search_params)

        # compose URL for arxiv.org API
        self.url = (
            f"https://export.arxiv.org/api/query?search_query={search_query}"
            f"&skip=0&max_results={self.max_query_results}&sortBy=relevance&sortOrder=descending"
        )
        print("URL: ", self.url)

        return True

    def parse_query_response_content(self) -> feedparser.FeedParserDict:
        """
        In this function, we parse the response content
        :return: feedparser.FeedParserDict object. This object is a dictionary-like
                 object that represents the parsed feed
        """
        # add OpenSearch specification to _FeedParserMixin.namespace under key 'opensearch', which defines a standard
        # for representing search results in RSS or Atom feeds
        feedparser.mixin._FeedParserMixin.namespaces[
            "http://a9.com/-/spec/opensearch/1.1/"
        ] = "opensearch"
        # add arxiv namespace to _FeedParserMixin.namespace under key 'arxiv', which defines the arXiv Atom feed
        feedparser.mixin._FeedParserMixin.namespaces[
            "http://arxiv.org/schemas/atom"
        ] = "arxiv"
        return feedparser.parse(self.response.content)

    def create_query_metadata_result(self) -> [dict, list[dict]]:
        """
        In this function, we create a query metadata dictionary and a list of query results
        :return: query metadata dictionary and a list of query results
        """
        query = {}

        # access the id of the query
        query["id"] = self.feed.get("feed").get("id").split("/")[-1]

        # access the response status code
        query["status"] = self.response.status_code
        # access the query
        query["query"] = self.feed.get("feed").get("title")
        # set max results
        query["max_results"] = self.max_query_results
        # access the time of the query
        # Parse the RFC 1123 date string into a datetime object
        timestamp = datetime.strptime(
            self.response.headers["Date"], "%a, %d %b %Y %H:%M:%S %Z"
        )
        # Convert the datetime object to the desired ISO 8601 format
        query["timestamp"] = timestamp.strftime("%Y-%m-%dT%H:%M:%S")
        # access the total number of results
        query["num_results"] = self.feed.get("feed").get("opensearch_totalresults")

        if query["num_results"] == "0":
            return query, []

        query_results = self.create_query_results_array(
            query_id=query["id"], feed_entries=self.feed["entries"]
        )

        return query, query_results

    @staticmethod
    def create_query_results_array(query_id, feed_entries) -> list[dict]:
        """
        In this function, we create a list of query results
        :param query_id: ID of the query
        :param feed_entries: List of feed entries
        :return: List of query results
        """
        query_results = []
        for entry in feed_entries:
            query = {}
            query["query_id"] = query_id

            # access author information (returned as list)
            list_of_authors = [author.get("name") for author in entry.get("authors")]
            authors = ", ".join(list_of_authors)

            query["author"] = authors
            query["title"] = entry.get("title")
            query["journal"] = entry.get("arxiv_journal_ref")
            query["time_of_storage"] = datetime.now()
            query_results.append(query)

        return query_results

    def query_arxiv_store_in_db(self) -> int:
        """
        In this function, we search arxiv.org for the given author, title, and journal
        We then store the query metadata and results in the database
        :return: status code of the query
        """
        # Create a DatabaseQueries object
        db_queries = DatabaseQueries()

        # query arxiv.org with the URL
        try:
            self.response = requests.get(self.url, verify=False)
        except Exception as e:
            print(f"Failed to query arXiv API: {e}")
            return 421

        # parse response content
        self.feed = self.parse_query_response_content()

        # Create a query metadata dictionary
        query_metadata, query_results = self.create_query_metadata_result()
        # If no results are found, store the query metadata and return
        if query_metadata["num_results"] == "0":
            try:
                db_queries.insert_into_table(table=QueryMetadata, data=query_metadata)
                db_queries.commit_session()
                return 422
            except Exception as e:
                print(f"Failed to store query metadata in the database: {e}")
                return 422

        # If the query ID does not exist in the database, store the query metadata and results
        if not db_queries.check_if_query_id_exists(query_id=query_metadata["id"]):
            try:
                db_queries.insert_into_table(table=QueryMetadata, data=query_metadata)
                db_queries.insert_into_table(table=QueryResults, data=query_results)
                db_queries.commit_session()
                return 200
            except Exception as e:
                print(f"Failed to store query and results in the database: {e}")
                return 423
        else:
            return 424
