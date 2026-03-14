"""Abstract base class for database adapters.

This module defines the interface that all database adapters must implement,
following the Open-Close Principle (open for extension, closed for modification).
"""
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator


class DatabaseAdapter(ABC):
    """Abstract base class for database adapters.

    Each database type (PostgreSQL, MySQL, SQLite, etc.) should implement
    this interface to provide database-specific functionality.
    """

    def __init__(self, connection_url: str):
        """Initialize the adapter with a connection URL.

        Args:
            connection_url: Database connection URL
        """
        self.connection_url = connection_url
        self._connection_params = self._parse_connection_url(connection_url)

    @property
    @abstractmethod
    def database_type(self) -> str:
        """Return the database type identifier.

        Returns:
            Database type string (e.g., 'postgresql', 'mysql')
        """
        pass

    @property
    @abstractmethod
    def sql_dialect(self) -> str:
        """Return the SQL dialect for sqlglot.

        Returns:
            Dialect string for sqlglot (e.g., 'postgres', 'mysql')
        """
        pass

    @abstractmethod
    def _parse_connection_url(self, url: str) -> dict[str, Any]:
        """Parse connection URL into components.

        Args:
            url: Database connection URL

        Returns:
            Dictionary containing connection parameters
        """
        pass

    @abstractmethod
    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Create an async database connection context manager.

        Yields:
            Database connection or cursor
        """
        pass

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test if the database connection is valid.

        Returns:
            True if connection successful, False otherwise
        """
        pass

    @abstractmethod
    async def execute_query(
        self,
        sql: str
    ) -> tuple[list[str], list[dict[str, Any]], float]:
        """Execute a SQL query and return results.

        Args:
            sql: SQL query to execute

        Returns:
            Tuple of (column_names, rows_as_dicts, query_time_seconds)
        """
        pass

    @abstractmethod
    async def get_tables_and_views(self) -> list[dict[str, Any]]:
        """Get all tables and views from the database.

        Returns:
            List of table/view metadata with structure:
            [
                {
                    "name": "table_name",
                    "type": "table" | "view",
                    "columns": [...]
                }
            ]
        """
        pass

    @abstractmethod
    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        """Get column information for a specific table.

        Args:
            table_name: Name of the table

        Returns:
            List of column metadata with structure:
            [
                {
                    "name": "column_name",
                    "dataType": "data_type",
                    "isNullable": bool,
                    "isPrimaryKey": bool,
                    "defaultValue": str | None
                }
            ]
        """
        pass

    @abstractmethod
    def get_llm_system_prompt(self, schema_description: str) -> str:
        """Generate database-specific LLM system prompt.

        Args:
            schema_description: Formatted schema description

        Returns:
            System prompt for LLM
        """
        pass

    def get_schema_description(self, tables: list[dict[str, Any]]) -> str:
        """Generate a text description of table schema for LLM context.

        This is a common implementation that can be overridden if needed.

        Args:
            tables: List of table metadata

        Returns:
            Formatted schema description
        """
        lines = ["Available tables and views:"]

        for table in tables:
            lines.append(f"\nTable: {table['name']} ({table['type']})")
            for col in table["columns"]:
                pk = " (PK)" if col["isPrimaryKey"] else ""
                nullable = " NULL" if col["isNullable"] else " NOT NULL"
                lines.append(f"  - {col['name']}: {col['dataType']}{nullable}{pk}")

        return "\n".join(lines)
