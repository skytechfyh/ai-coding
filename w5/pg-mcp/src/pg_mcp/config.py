from __future__ import annotations

from urllib.parse import quote_plus

from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseConfig(BaseModel):
    alias: str
    host: str = "localhost"
    port: int = 5432
    dbname: str
    user: str
    password: SecretStr
    schemas: list[str] = Field(default_factory=lambda: ["public"])
    min_pool_size: int = 1
    max_pool_size: int = 5

    @property
    def dsn(self) -> str:
        pwd = self.password.get_secret_value()
        # P1修复: URL 编码防止密码中的特殊字符破坏 DSN 解析
        return f"postgresql://{quote_plus(self.user)}:{quote_plus(pwd)}@{self.host}:{self.port}/{self.dbname}"


class OpenAIConfig(BaseModel):
    api_key: SecretStr
    model: str = "gpt-4o-mini"
    timeout_seconds: float = 10.0


class ServerConfig(BaseModel):
    query_timeout_seconds: int = 30
    result_validation_sample_rows: int = 5
    max_result_rows: int = 1000
    auto_retry_on_invalid: bool = False


class AppConfig(BaseSettings):
    databases: list[DatabaseConfig]
    openai: OpenAIConfig
    server: ServerConfig = ServerConfig()

    model_config = SettingsConfigDict(
        env_file=".env",
        env_nested_delimiter="__",
        yaml_file="config.yaml",
    )
