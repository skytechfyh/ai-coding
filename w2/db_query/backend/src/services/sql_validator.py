"""SQL validation and LIMIT injection service."""
import sqlglot
from sqlglot import exp


class SQLValidationError(Exception):
    """Exception raised when SQL validation fails."""
    pass


def validate_and_fix_sql(sql: str) -> tuple[str, bool, str]:
    """Validate SQL and add LIMIT if missing.

    Args:
        sql: SQL query to validate

    Returns:
        Tuple of (fixed_sql, is_valid, error_message)
    """
    try:
        # Strip trailing semicolon for parsing
        sql = sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1].strip()

        statements = sqlglot.parse(sql)
        if not statements:
            return "", False, "Empty SQL"

        stmt = statements[0]

        # Check if it's a SELECT statement
        if not isinstance(stmt, exp.Select):
            return "", False, "Only SELECT statements are allowed"

        # Check if LIMIT already exists
        if not stmt.find(exp.Limit):
            # Add LIMIT 1000
            stmt.set("limit", exp.Limit(expression=exp.Literal.number(1000)))
            return stmt.sql(), True, ""
        else:
            return sql, True, ""

    except sqlglot.errors.ParseError as e:
        return "", False, f"SQL syntax error: {str(e)}"
    except Exception as e:
        return "", False, f"Error parsing SQL: {str(e)}"
