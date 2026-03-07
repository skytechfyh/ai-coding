"""Database connection service."""
import os
from contextlib import contextmanager
from typing import Any, Generator

import psycopg2
import pymysql


class DatabaseConnectionError(Exception):
    """Exception raised when database connection fails."""
    pass


def get_database_type(url: str) -> str:
    """Detect database type from connection URL.

    Args:
        url: Database connection URL

    Returns:
        Database type string: 'postgresql', 'mysql', or 'unknown'
    """
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return "postgresql"
    elif url.startswith("mysql://") or url.startswith("mysql+pymysql://"):
        return "mysql"
    else:
        return "unknown"


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
    elif url.startswith("mysql://") or url.startswith("mysql+pymysql://"):
        # Parse MySQL URL
        # Format: mysql://user:password@host:port/database
        # Remove mysql:// or mysql+pymysql:// prefix
        url_without_prefix = url.replace("mysql+pymysql://", "").replace("mysql://", "")

        # Parse connection string
        parts = url_without_prefix.split("@")
        if len(parts) != 2:
            raise DatabaseConnectionError("Invalid MySQL URL format")

        user_pass = parts[0].split(":")
        host_db = parts[1].split("/")

        if len(user_pass) != 2 or len(host_db) != 2:
            raise DatabaseConnectionError("Invalid MySQL URL format")

        user = user_pass[0]
        password = user_pass[1]
        host_port = host_db[0].split(":")
        host = host_port[0]
        port = int(host_port[1]) if len(host_port) > 1 else 3306
        database = host_db[1]

        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            cursorclass=pymysql.cursors.DictCursor
        )
        try:
            yield conn.cursor()
        except pymysql.Error as e:
            raise DatabaseConnectionError(f"MySQL error: {str(e)}")
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
    except (psycopg2.Error, pymysql.Error, DatabaseConnectionError) as e:
        # Log specific database errors for debugging
        print(f"Connection test failed: {str(e)}")
        return False
    except Exception as e:
        print(f"Unexpected error during connection test: {str(e)}")
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

        # Handle different cursor types
        if url.startswith("mysql://") or url.startswith("mysql+pymysql://"):
            # MySQL with DictCursor returns dict rows directly
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result_rows = rows  # Already in dict format
        else:
            # PostgreSQL returns tuples
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            result_rows = [dict(zip(columns, row)) for row in rows]

    query_time = time.time() - start_time

    return columns, result_rows, query_time
