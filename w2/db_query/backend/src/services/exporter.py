"""Export service for CSV and JSON formats."""
import csv
import io
from typing import Any


def export_to_csv(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Export query results to CSV format.

    Args:
        columns: List of column names
        rows: List of row dictionaries

    Returns:
        CSV string
    """
    output = io.StringIO()
    writer = csv.writer(output)

    # Write header
    writer.writerow(columns)

    # Write rows
    for row in rows:
        writer.writerow([row.get(col, "") for col in columns])

    return output.getvalue()


def export_to_json(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Export query results to JSON format.

    Args:
        columns: List of column names
        rows: List of row dictionaries

    Returns:
        JSON string
    """
    import json

    return json.dumps({"columns": columns, "rows": rows}, indent=2, default=str)
