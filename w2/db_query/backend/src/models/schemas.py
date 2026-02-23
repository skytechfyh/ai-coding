"""Pydantic models for API requests and responses."""
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# Request Models
class CreateDatabaseRequest(BaseModel):
    """Request model for creating a database connection."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    url: str = Field(..., description="Database connection URL")


class QueryRequest(BaseModel):
    """Request model for executing SQL query."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sql: str = Field(..., description="SQL query to execute", max_length=10000)


class NaturalLanguageRequest(BaseModel):
    """Request model for natural language to SQL."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    prompt: str = Field(..., description="Natural language query", max_length=2000)


# Response Models
class ColumnResponse(BaseModel):
    """Response model for a table column."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str
    dataType: str
    isNullable: bool
    isPrimaryKey: bool
    defaultValue: str | None = None


class TableMetadataResponse(BaseModel):
    """Response model for table metadata."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str
    type: str  # table or view
    columns: list[ColumnResponse]


class DatabaseResponse(BaseModel):
    """Response model for database connection."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str
    databaseType: str
    createdAt: datetime
    lastUsedAt: datetime | None = None


class DatabaseWithMetadataResponse(BaseModel):
    """Response model for database with full metadata."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    name: str
    databaseType: str
    tables: list[TableMetadataResponse]


class QueryResultResponse(BaseModel):
    """Response model for query result."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    columns: list[str]
    rows: list[dict[str, Any]]
    totalRows: int
    queryTime: float


class NaturalLanguageResponse(BaseModel):
    """Response model for natural language SQL generation."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    sql: str
    needsConfirmation: bool = False


class DatabaseListResponse(BaseModel):
    """Response model for list of databases."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    databases: list[DatabaseResponse]


class ApiResponse(BaseModel):
    """Generic API response wrapper."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
    )

    success: bool
    data: Any = None
    errorMessage: str | None = None
