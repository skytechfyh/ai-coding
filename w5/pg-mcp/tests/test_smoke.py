"""Smoke tests: 验证导入链路无循环依赖，模块可正常 import。"""


def test_import_models() -> None:
    from pg_mcp.models import (
        TableSchema,
        DatabaseSchemaCache,
        QueryToSqlOutput,
        QueryToResultOutput,
        ValidationInfo,
        DatabaseInfo,
        ListDatabasesOutput,
        RefreshSchemaOutput,
        ExecutionResult,
        ColumnInfo,
        IndexInfo,
        ForeignKeyInfo,
        CustomTypeInfo,
    )
    assert TableSchema is not None
    assert DatabaseSchemaCache is not None


def test_import_config() -> None:
    from pg_mcp.config import AppConfig, DatabaseConfig, OpenAIConfig, ServerConfig
    assert AppConfig is not None


def test_import_sql_validator() -> None:
    from pg_mcp.sql_validator import validate_sql
    assert validate_sql is not None


def test_import_nl2sql() -> None:
    from pg_mcp.nl2sql import generate_sql, build_schema_text
    assert generate_sql is not None
    assert build_schema_text is not None


def test_import_result_validator() -> None:
    from pg_mcp.result_validator import validate_result
    assert validate_result is not None


def test_import_schema_cache() -> None:
    from pg_mcp.schema_cache import load_schema
    assert load_schema is not None


def test_import_db_executor() -> None:
    from pg_mcp.db_executor import create_pool, execute_query
    assert create_pool is not None
    assert execute_query is not None


def test_import_server() -> None:
    from pg_mcp.server import mcp
    assert mcp is not None
