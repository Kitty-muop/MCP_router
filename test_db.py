import sqlite3
from app.database import init_db, get_db_conn


def test_init_db(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(str(db_path))
    conn = sqlite3.connect(str(db_path))
    tables = [
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table';"
        ).fetchall()
    ]
    assert "api_keys" in tables
    assert "token_usage" in tables
    conn.close()


def test_get_db_conn(tmp_path):
    db_path = tmp_path / "app.db"
    init_db(str(db_path))
    conn = get_db_conn(str(db_path))
    assert isinstance(conn, sqlite3.Connection)
    conn.close()
