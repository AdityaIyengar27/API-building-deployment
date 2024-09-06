import os

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class QueryMetadata(Base):
    """
    Table to store metadata of queries made to arXiv API
    """

    __tablename__ = "query_metadata"
    id = Column(String, primary_key=True)
    query = Column(String, nullable=False)
    num_results = Column(Integer)
    max_results = Column(Integer)
    status = Column(Integer)
    timestamp = Column(DateTime, nullable=False)


class QueryResults(Base):
    """
    Table to store results of queries made to arXiv API
    """

    __tablename__ = "query_results"
    # Create the sequence
    # sequence = Sequence('query_results_id_seq')
    id = Column(Integer, primary_key=True, autoincrement=True)
    query_id = Column(String, ForeignKey("query_metadata.id"))
    author = Column(String, nullable=True)
    title = Column(String, nullable=False)
    journal = Column(String, nullable=True)
    time_of_storage = Column(DateTime, nullable=False)


class DatabaseServerOperations:
    """
    Class to perform operations on the PostgreSQL database server
    We create the database URL, engine, and tables if they do not already exist
    """

    def __init__(self):
        """
        Initialize the DatabaseServerOperations class
        """
        self.user = os.getenv("DB_USER")
        self.password = os.getenv("DB_PASSWORD")
        self.database = os.getenv("DB_NAME")
        self.port = os.getenv("DB_PORT")
        # Create the user postgres database URLs
        self.db_url = self.make_db_url()
        self.create_table_if_not_exists()

    def make_db_url(self) -> str:
        """
        Create the user URL for the PostgreSQL database
        :return: URL object for the user database
        """
        db_url = f"postgresql+psycopg2://{self.user}:{self.password}@db:{self.port}/{self.database}"
        return db_url

    def create_engine(self) -> create_engine:
        """
        Create a SQLAlchemy engine connected to the PostgreSQL database
        :return: create_engine: SQLAlchemy create_engine object
        """
        return create_engine(self.db_url)

    @staticmethod
    def create_session(engine: create_engine) -> sessionmaker.object_session:
        """
        Create a SQLAlchemy session
        :param engine:
        :return: session: SQLAlchemy session object
        """
        session_maker = sessionmaker(bind=engine)
        session = session_maker()
        return session

    def create_table_if_not_exists(self):
        """
        Create tables in the PostgreSQL database if they do not already exist
        :return: None
        """
        engine = self.create_engine()
        QueryMetadata.__table__.create(bind=engine, checkfirst=True)
        QueryResults.__table__.create(bind=engine, checkfirst=True)
