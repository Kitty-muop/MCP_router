import sqlite3


def init_db(db_path="app.db"):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY, provider TEXT, key_value TEXT)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS token_usage (id INTEGER PRIMARY KEY, key_id INTEGER, tokens INTEGER, date TEXT)"
    )
    conn.commit()
    conn.close()


def get_db_conn(db_path="app.db"):
    return sqlite3.connect(db_path)
