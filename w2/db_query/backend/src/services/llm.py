"""LLM service for natural language to SQL generation."""
import os

from anthropic import Anthropic
from anthropic.types import TextBlock, ThinkingBlock

from .metadata import get_table_schema_description


class LLMError(Exception):
    """Exception raised when LLM generation fails."""
    pass


def generate_sql_from_natural_language(
    url: str,
    prompt: str,
    tables: list[dict[str, str]],
) -> tuple[str, bool, str]:
    """Generate SQL from natural language using LLM (Claude API).

    Args:
        url: Database connection URL (for context)
        prompt: Natural language query
        tables: List of table metadata

    Returns:
        Tuple of (generated_sql, needs_confirmation, error_message)
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "", False, "ANTHROPIC_API_KEY environment variable not set"

    base_url = os.getenv("ANTHROPIC_BASE_URL")

    # Generate schema description
    schema_description = get_table_schema_description(tables)

    system_prompt = f"""You are a PostgreSQL SQL expert. Given a natural language query,
generate a valid PostgreSQL SELECT statement.

{schema_description}

Rules:
1. Only generate SELECT statements - never INSERT, UPDATE, DELETE, CREATE, DROP, etc.
2. Always include LIMIT 1000 unless the query has its own LIMIT
3. Use proper table and column names from the schema
4. Use correct PostgreSQL syntax
5. If the query cannot be determined, return an error message starting with "ERROR:"

Return ONLY the SQL statement, no explanations or markdown."""

    user_prompt = f"Generate SQL for: {prompt}"

    try:
        client = Anthropic(api_key=api_key, base_url=base_url) if base_url else Anthropic(api_key=api_key)
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            temperature=0,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_prompt}
            ],
        )

        # Handle different content block types
        generated_sql = ""
        for block in response.content:
            if isinstance(block, TextBlock):
                generated_sql = block.text.strip()
                break
            elif isinstance(block, ThinkingBlock):
                # Skip thinking blocks
                continue

        if not generated_sql:
            return "", False, "LLM returned empty response"

        # Check for error in response
        if generated_sql.startswith("ERROR:"):
            return "", False, generated_sql

        return generated_sql, False, ""

    except Exception as e:
        return "", False, f"LLM error: {str(e)}"
