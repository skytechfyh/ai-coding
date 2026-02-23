"""SQLite storage for database connections and metadata."""
import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


def get_db_path() -> Path:
    """Get the path to the SQLite database file."""
    db_dir = Path.home() / ".db_query"
    db_dir.mkdir(parents=True, exist_ok=True)
    return db_dir / "db_query.db"


def init_db() -> None:
    """Initialize the SQLite database schema."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    # Database connections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS database_connections (
            id TEXT PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            url TEXT NOT NULL,
            database_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            last_used_at TEXT
        )
    """)

    # Table metadata cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS table_metadata (
            id TEXT PRIMARY KEY,
            database_id TEXT NOT NULL,
            name TEXT NOT NULL,
            type TEXT NOT NULL,
            columns_json TEXT NOT NULL,
            cached_at TEXT NOT NULL,
            FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE,
            UNIQUE(database_id, name)
        )
    """)

    # Query history
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id TEXT PRIMARY KEY,
            database_id TEXT NOT NULL,
            sql TEXT NOT NULL,
            executed_at TEXT NOT NULL,
            row_count INTEGER,
            duration REAL,
            status TEXT NOT NULL,
            FOREIGN KEY (database_id) REFERENCES database_connections(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def get_connection(name: str) -> dict[str, Any] | None:
    """Get a database connection by name."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM database_connections WHERE name = ?",
        (name,)
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row["id"],
            "name": row["name"],
            "url": row["url"],
            "database_type": row["database_type"],
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
        }
    return None


def get_all_connections() -> list[dict[str, Any]]:
    """Get all database connections."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM database_connections ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "url": row["url"],
            "database_type": row["database_type"],
            "created_at": row["created_at"],
            "last_used_at": row["last_used_at"],
        }
        for row in rows
    ]


def create_connection(name: str, url: str, database_type: str) -> dict[str, Any]:
    """Create a new database connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    db_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO database_connections (id, name, url, database_type, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (db_id, name, url, database_type, now),
    )
    conn.commit()
    conn.close()

    return {
        "id": db_id,
        "name": name,
        "url": url,
        "database_type": database_type,
        "created_at": now,
        "last_used_at": None,
    }


def delete_connection(name: str) -> bool:
    """Delete a database connection by name."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute("DELETE FROM database_connections WHERE name = ?", (name,))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()

    return deleted


def update_last_used(name: str) -> None:
    """Update the last used timestamp for a connection."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    now = datetime.now().isoformat()
    cursor.execute(
        "UPDATE database_connections SET last_used_at = ? WHERE name = ?",
        (now, name),
    )
    conn.commit()
    conn.close()


def save_table_metadata(
    database_id: str, name: str, type_: str, columns: list[dict[str, Any]]
) -> None:
    """Save table metadata to cache."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    metadata_id = str(uuid.uuid4())
    now = datetime.now().isoformat()
    columns_json = json.dumps(columns)

    cursor.execute(
        """
        INSERT OR REPLACE INTO table_metadata (id, database_id, name, type, columns_json, cached_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (metadata_id, database_id, name, type_, columns_json, now),
    )
    conn.commit()
    conn.close()


def get_table_metadata(database_id: str, name: str) -> dict[str, Any] | None:
    """Get table metadata from cache."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM table_metadata WHERE database_id = ? AND name = ?",
        (database_id, name),
    )
    row = cursor.fetchone()
    conn.close()

    if row:
        return {
            "id": row["id"],
            "database_id": row["database_id"],
            "name": row["name"],
            "type": row["type"],
            "columns": json.loads(row["columns_json"]),
            "cached_at": row["cached_at"],
        }
    return None


def get_all_table_metadata(database_id: str) -> list[dict[str, Any]]:
    """Get all table metadata for a database."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM table_metadata WHERE database_id = ? ORDER BY name",
        (database_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "database_id": row["database_id"],
            "name": row["name"],
            "type": row["type"],
            "columns": json.loads(row["columns_json"]),
            "cached_at": row["cached_at"],
        }
        for row in rows
    ]


def parse_database_type(url: str) -> str:
    """Parse database type from connection URL."""
    if url.startswith("postgres://") or url.startswith("postgresql://"):
        return "postgres"
    elif url.startswith("mysql://"):
        return "mysql"
    elif url.startswith("sqlite://"):
        return "sqlite"
    return "unknown"


def save_query_history(
    database_id: str, sql: str, row_count: int, duration: float, status: str
) -> None:
    """Save a query to history."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    history_id = str(uuid.uuid4())
    now = datetime.now().isoformat()

    cursor.execute(
        """
        INSERT INTO query_history (id, database_id, sql, executed_at, row_count, duration, status)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (history_id, database_id, sql, now, row_count, duration, status),
    )
    conn.commit()
    conn.close()


def get_query_history(database_id: str, limit: int = 50) -> list[dict[str, Any]]:
    """Get query history for a database."""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT * FROM query_history
        WHERE database_id = ?
        ORDER BY executed_at DESC
        LIMIT ?
        """,
        (database_id, limit),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "database_id": row["database_id"],
            "sql": row["sql"],
            "executed_at": row["executed_at"],
            "row_count": row["row_count"],
            "duration": row["duration"],
            "status": row["status"],
        }
        for row in rows
    ]
