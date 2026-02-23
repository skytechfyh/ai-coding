"""Metadata extraction service for database tables and views."""
from typing import Any

import psycopg2


def get_tables_and_views(url: str) -> list[dict[str, Any]]:
    """Get all tables and views from a PostgreSQL database.

    Args:
        url: Database connection URL

    Returns:
        List of table/view metadata
    """
    conn = psycopg2.connect(url)
    cursor = conn.cursor()

    # Query to get all tables and views
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
        table_name, table_type = row
        table_type = "view" if table_type == "VIEW" else "table"

        # Get column information
        columns = get_columns(url, table_name)

        tables.append({
            "name": table_name,
            "type": table_type,
            "columns": columns,
        })

    cursor.close()
    conn.close()

    return tables


def get_columns(url: str, table_name: str) -> list[dict[str, str]]:
    """Get column information for a table.

    Args:
        url: Database connection URL
        table_name: Name of the table

    Returns:
        List of column metadata
    """
    conn = psycopg2.connect(url)
    cursor = conn.cursor()

    # Query to get column information
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
        column_name, data_type, is_nullable, default_value, is_primary_key = row
        columns.append({
            "name": column_name,
            "dataType": data_type,
            "isNullable": is_nullable == "YES",
            "isPrimaryKey": is_primary_key,
            "defaultValue": default_value,
        })

    cursor.close()
    conn.close()

    return columns


def get_table_schema_description(tables: list[dict[str, Any]]) -> str:
    """Generate a text description of table schema for LLM context.

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
