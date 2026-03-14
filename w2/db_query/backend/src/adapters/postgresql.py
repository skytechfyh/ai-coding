"""PostgreSQL database adapter implementation."""
import time
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator
from urllib.parse import urlparse

import psycopg2
import psycopg2.extras

from .base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    """PostgreSQL-specific database adapter.

    Implements the DatabaseAdapter interface for PostgreSQL databases.
    Uses psycopg2 for synchronous operations (async version with asyncpg
    can be implemented later if needed).
    """

    @property
    def database_type(self) -> str:
        """Return 'postgresql' as the database type identifier."""
        return "postgresql"

    @property
    def sql_dialect(self) -> str:
        """Return 'postgres' for sqlglot dialect."""
        return "postgres"

    def _parse_connection_url(self, url: str) -> dict[str, Any]:
        """Parse PostgreSQL connection URL.

        Args:
            url: PostgreSQL connection URL (postgres:// or postgresql://)

        Returns:
            Dictionary with connection parameters
        """
        parsed = urlparse(url)
        return {
            "host": parsed.hostname,
            "port": parsed.port or 5432,
            "user": parsed.username,
            "password": parsed.password,
            "database": parsed.path.lstrip("/") if parsed.path else None,
        }

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[Any, None]:
        """Create a PostgreSQL connection context manager.

        Yields:
            psycopg2 cursor with DictCursor for dict-like row access
        """
        conn = psycopg2.connect(self.connection_url)
        cursor = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        try:
            yield cursor
        finally:
            cursor.close()
            conn.close()

    async def test_connection(self) -> bool:
        """Test PostgreSQL connection validity.

        Returns:
            True if connection successful, False otherwise
        """
        try:
            async with self.get_connection() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except psycopg2.Error as e:
            print(f"PostgreSQL connection test failed: {e}")
            return False
        except Exception as e:
            print(f"Unexpected error during PostgreSQL connection test: {e}")
            return False

    async def execute_query(
        self,
        sql: str
    ) -> tuple[list[str], list[dict[str, Any]], float]:
        """Execute a SQL query on PostgreSQL.

        Args:
            sql: SQL query to execute

        Returns:
            Tuple of (column_names, rows_as_dicts, query_time_seconds)
        """
        start_time = time.time()

        async with self.get_connection() as cursor:
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            # Convert DictRow to regular dict
            result_rows = [dict(row) for row in rows]

        query_time = time.time() - start_time
        return columns, result_rows, query_time

    async def get_tables_and_views(self) -> list[dict[str, Any]]:
        """Get all tables and views from PostgreSQL database.

        Returns:
            List of table/view metadata
        """
        async with self.get_connection() as cursor:
            cursor.execute("""
                SELECT
                    table_name,
                    table_type
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
            """)

            tables = []
            for row in cursor.fetchall():
                table_name = row["table_name"]
                table_type = "view" if row["table_type"] == "VIEW" else "table"

                columns = await self.get_columns(table_name)

                tables.append({
                    "name": table_name,
                    "type": table_type,
                    "columns": columns,
                })

            return tables

    async def get_columns(self, table_name: str) -> list[dict[str, Any]]:
        """Get column information for a PostgreSQL table.

        Args:
            table_name: Name of the table

        Returns:
            List of column metadata
        """
        async with self.get_connection() as cursor:
            cursor.execute("""
                SELECT
                    c.column_name,
                    c.data_type,
                    c.is_nullable,
                    c.column_default,
                    CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                FROM information_schema.columns c
                LEFT JOIN (
                    SELECT ku.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage ku
                        ON tc.constraint_name = ku.constraint_name
                        AND tc.table_schema = ku.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                        AND ku.table_name = %s
                        AND ku.table_schema = 'public'
                ) pk ON c.column_name = pk.column_name
                WHERE c.table_name = %s
                    AND c.table_schema = 'public'
                ORDER BY c.ordinal_position
            """, (table_name, table_name))

            columns = []
            for row in cursor.fetchall():
                columns.append({
                    "name": row["column_name"],
                    "dataType": row["data_type"],
                    "isNullable": row["is_nullable"] == "YES",
                    "isPrimaryKey": row["is_primary_key"],
                    "defaultValue": row["column_default"],
                })

            return columns

    def get_llm_system_prompt(self, schema_description: str) -> str:
        """Generate PostgreSQL-specific LLM system prompt.

        Args:
            schema_description: Formatted schema description

        Returns:
            System prompt for LLM
        """
        return f"""You are a PostgreSQL SQL expert. Given a natural language query,
generate a valid PostgreSQL SELECT statement.

{schema_description}

Rules:
1. Only generate SELECT statements - never INSERT, UPDATE, DELETE, CREATE, DROP, etc.
2. Always include LIMIT 1000 unless the query has its own LIMIT
3. Use proper table and column names from the schema
4. Use correct PostgreSQL syntax
5. If the query cannot be determined, return an error message starting with "ERROR:"

Return ONLY the SQL statement, no explanations or markdown."""
