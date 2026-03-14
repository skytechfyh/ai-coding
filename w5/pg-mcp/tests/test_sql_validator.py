"""SQL 验证器单元测试（纯函数，无需 mock）"""
import pytest
from pg_mcp.sql_validator import validate_sql


# ── 正常通过的 SQL ─────────────────────────────────────────────────────────

PASS_CASES = [
    "SELECT * FROM users",
    "SELECT id, name FROM orders WHERE status = 'active'",
    "SELECT * FROM users LIMIT 5",
    "WITH cte AS (SELECT 1 AS n) SELECT * FROM cte",
    "SELECT a.id FROM users a JOIN orders b ON a.id = b.uid",
    "SELECT COUNT(*) FROM events WHERE created_at >= NOW() - INTERVAL '30 days'",
    "SELECT id, email FROM users WHERE email ILIKE '%@example.com'",
]

# ── 应被拒绝的 SQL ─────────────────────────────────────────────────────────

FAIL_CASES = [
    ("INSERT INTO users VALUES (1, 'x')", "Only SELECT"),
    ("UPDATE users SET name='x'", "Only SELECT"),
    ("DROP TABLE users", "Only SELECT"),
    ("DELETE FROM users WHERE id = 1", "Only SELECT"),
    ("CREATE TABLE t (id int)", "Only SELECT"),
    ("SELECT * FROM users; DELETE FROM users", "Multiple"),
    ("SELECT * FROM users -- comment", "comments"),
    ("SELECT * FROM users /* block */", "comments"),
    ("", "Only SELECT"),
]


@pytest.mark.parametrize("sql", PASS_CASES)
def test_valid_sql_passes(sql: str) -> None:
    out, err = validate_sql(sql)
    assert err is None, f"Expected pass but got error: {err}"
    assert len(out) > 0


@pytest.mark.parametrize("sql,err_substring", FAIL_CASES)
def test_invalid_sql_rejected(sql: str, err_substring: str) -> None:
    _, err = validate_sql(sql)
    assert err is not None, f"Expected rejection but SQL passed: {sql!r}"
    assert err_substring.lower() in err.lower(), (
        f"Expected '{err_substring}' in error: {err}"
    )


def test_limit_injection_when_no_limit() -> None:
    out, err = validate_sql("SELECT * FROM t", max_rows=50)
    assert err is None
    assert "50" in out  # LIMIT 50 should be injected


def test_existing_limit_preserved() -> None:
    out, err = validate_sql("SELECT * FROM t LIMIT 5", max_rows=1000)
    assert err is None
    assert "5" in out
    # LIMIT 1000 should NOT be injected (already has LIMIT 5)
    assert "1000" not in out


def test_limit_injection_default() -> None:
    out, err = validate_sql("SELECT id FROM users")
    assert err is None
    assert "1000" in out  # default max_rows=1000


def test_cte_passes() -> None:
    sql = "WITH ranked AS (SELECT id, ROW_NUMBER() OVER (ORDER BY created_at) AS rn FROM users) SELECT * FROM ranked WHERE rn <= 10"
    out, err = validate_sql(sql)
    assert err is None


def test_returns_postgres_dialect() -> None:
    out, err = validate_sql("SELECT * FROM users")
    assert err is None
    # Should be valid SQL string
    assert "SELECT" in out.upper()
