"""Database connection service."""
import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2


class DatabaseConnectionError(Exception):
    """Exception raised when database connection fails."""
    pass


@contextmanager
def get_db_connection(url: str) -> Generator[Any, None, None]:
    """Create a database connection context manager.

    Args:
        url: Database connection URL

    Yields:
        Database connection cursor

    Raises:
        DatabaseConnectionError: If connection fails
    """
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        # Parse PostgreSQL URL
        # Format: postgres://user:password@host:port/database
        conn = psycopg2.connect(url)
        try:
            yield conn.cursor()
        finally:
            conn.close()
    else:
        raise DatabaseConnectionError(f"Unsupported database type: {url}")


def test_connection(url: str) -> bool:
    """Test if a database connection is valid.

    Args:
        url: Database connection URL

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_db_connection(url) as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        return True
    except Exception:
        return False


def execute_query(url: str, sql: str) -> tuple[list[str], list[dict[str, Any]], float]:
    """Execute a SQL query and return results.

    Args:
        url: Database connection URL
        sql: SQL query to execute

    Returns:
        Tuple of (columns, rows, query_time)
    """
    import time

    start_time = time.time()

    with get_db_connection(url) as cursor:
        cursor.execute(sql)
        columns = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()

    query_time = time.time() - start_time

    # Convert rows to list of dicts
    result_rows = [dict(zip(columns, row)) for row in rows]

    return columns, result_rows, query_time
