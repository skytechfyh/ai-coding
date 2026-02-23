"""API routes for database query tool."""
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException

from ..db import store
from ..models import schemas
from ..services import database, exporter, llm, metadata, sql_validator

router = APIRouter(prefix="/api/v1", tags=["database"])


@router.get("/dbs", response_model=schemas.DatabaseListResponse)
def list_databases() -> dict[str, Any]:
    """Get all saved database connections."""
    connections = store.get_all_connections()
    databases = [
        {
            "name": conn["name"],
            "databaseType": conn["database_type"],
            "createdAt": conn["created_at"],
            "lastUsedAt": conn["last_used_at"],
        }
        for conn in connections
    ]
    return {"databases": databases}


@router.put("/dbs/{name}", response_model=schemas.ApiResponse)
def create_database(name: str, request: schemas.CreateDatabaseRequest) -> dict[str, Any]:
    """Create a new database connection."""
    # Check if connection already exists
    existing = store.get_connection(name)
    if existing:
        raise HTTPException(status_code=409, detail=f"Database '{name}' already exists")

    # Test the connection first
    if not database.test_connection(request.url):
        raise HTTPException(status_code=400, detail="Failed to connect to database")

    # Determine database type
    database_type = store.parse_database_type(request.url)

    # Create connection in store
    store.create_connection(name, request.url, database_type)

    # Get metadata and cache it
    try:
        tables = metadata.get_tables_and_views(request.url)
        conn = store.get_connection(name)
        if conn:
            for table in tables:
                store.save_table_metadata(
                    conn["id"],
                    table["name"],
                    table["type"],
                    table["columns"],
                )
    except Exception as e:
        # If metadata extraction fails, still return success
        # User can refresh metadata later
        pass

    return {
        "success": True,
        "data": {"name": name, "databaseType": database_type},
        "errorMessage": None,
    }


@router.get("/dbs/{name}", response_model=schemas.ApiResponse)
def get_database(name: str) -> dict[str, Any]:
    """Get database metadata (tables and columns)."""
    # Get connection from store
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    # Try to get cached metadata first
    cached_tables = store.get_all_table_metadata(conn["id"])

    if cached_tables:
        tables = [
            {
                "name": t["name"],
                "type": t["type"],
                "columns": [
                    {
                        "name": c["name"],
                        "dataType": c["dataType"],
                        "isNullable": c["isNullable"],
                        "isPrimaryKey": c["isPrimaryKey"],
                        "defaultValue": c.get("defaultValue"),
                    }
                    for c in t["columns"]
                ],
            }
            for t in cached_tables
        ]
    else:
        # Fetch fresh metadata
        try:
            tables = metadata.get_tables_and_views(conn["url"])
            # Cache it
            for table in tables:
                store.save_table_metadata(
                    conn["id"],
                    table["name"],
                    table["type"],
                    table["columns"],
                )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to fetch metadata: {str(e)}"
            )

    # Update last used
    store.update_last_used(name)

    return {
        "success": True,
        "data": {
            "name": name,
            "databaseType": conn["database_type"],
            "tables": tables,
        },
        "errorMessage": None,
    }


@router.delete("/dbs/{name}", response_model=schemas.ApiResponse)
def delete_database(name: str) -> dict[str, Any]:
    """Delete a database connection."""
    deleted = store.delete_connection(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    return {
        "success": True,
        "data": None,
        "errorMessage": None,
    }


@router.post("/dbs/{name}/query", response_model=schemas.ApiResponse)
def execute_query(name: str, request: schemas.QueryRequest) -> dict[str, Any]:
    """Execute a SQL query on the database."""
    # Get connection
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    # Validate and fix SQL
    fixed_sql, is_valid, error_msg = sql_validator.validate_and_fix_sql(request.sql)
    if not is_valid:
        return {
            "success": False,
            "data": None,
            "errorMessage": error_msg,
        }

    # Execute query
    try:
        columns, rows, query_time = database.execute_query(conn["url"], fixed_sql)

        return {
            "success": True,
            "data": {
                "columns": columns,
                "rows": rows,
                "totalRows": len(rows),
                "queryTime": query_time,
            },
            "errorMessage": None,
        }
    except Exception as e:
        return {
            "success": False,
            "data": None,
            "errorMessage": str(e),
        }


@router.post("/dbs/{name}/query/natural", response_model=schemas.ApiResponse)
def natural_language_query(
    name: str,
    request: schemas.NaturalLanguageRequest,
) -> dict[str, Any]:
    """Generate SQL from natural language and optionally execute it."""
    # Get connection
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    # Get cached tables metadata
    cached_tables = store.get_all_table_metadata(conn["id"])
    if cached_tables:
        tables = cached_tables
    else:
        # Try to fetch fresh metadata
        try:
            tables = metadata.get_tables_and_views(conn["url"])
        except Exception as e:
            return {
                "success": False,
                "data": None,
                "errorMessage": f"Failed to fetch metadata: {str(e)}",
            }

    # Generate SQL using LLM
    generated_sql, needs_confirm, error_msg = llm.generate_sql_from_natural_language(
        conn["url"],
        request.prompt,
        tables,
    )

    if error_msg:
        return {
            "success": False,
            "data": None,
            "errorMessage": error_msg,
        }

    return {
        "success": True,
        "data": {
            "sql": generated_sql,
            "needsConfirmation": needs_confirm,
        },
        "errorMessage": None,
    }


@router.get("/dbs/{name}/history", response_model=schemas.ApiResponse)
def get_query_history(name: str) -> dict[str, Any]:
    """Get query history for a database."""
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    history = store.get_query_history(conn["id"])

    return {
        "success": True,
        "data": {"history": history},
        "errorMessage": None,
    }


@router.get("/dbs/{name}/export/csv", response_model=schemas.ApiResponse)
def export_csv(name: str, sql: str) -> dict[str, Any]:
    """Export query results to CSV."""
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    # Validate and fix SQL
    fixed_sql, is_valid, error_msg = sql_validator.validate_and_fix_sql(sql)
    if not is_valid:
        return {"success": False, "data": None, "errorMessage": error_msg}

    try:
        columns, rows, _ = database.execute_query(conn["url"], fixed_sql)
        csv_data = exporter.export_to_csv(columns, rows)

        # Save to query history
        store.save_query_history(conn["id"], sql, len(rows), 0, "success")

        return {
            "success": True,
            "data": {"csv": csv_data},
            "errorMessage": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "errorMessage": str(e)}


@router.get("/dbs/{name}/export/json", response_model=schemas.ApiResponse)
def export_json(name: str, sql: str) -> dict[str, Any]:
    """Export query results to JSON."""
    conn = store.get_connection(name)
    if not conn:
        raise HTTPException(status_code=404, detail=f"Database '{name}' not found")

    # Validate and fix SQL
    fixed_sql, is_valid, error_msg = sql_validator.validate_and_fix_sql(sql)
    if not is_valid:
        return {"success": False, "data": None, "errorMessage": error_msg}

    try:
        columns, rows, _ = database.execute_query(conn["url"], fixed_sql)
        json_data = exporter.export_to_json(columns, rows)

        # Save to query history
        store.save_query_history(conn["id"], sql, len(rows), 0, "success")

        return {
            "success": True,
            "data": {"json": json_data},
            "errorMessage": None,
        }
    except Exception as e:
        return {"success": False, "data": None, "errorMessage": str(e)}
