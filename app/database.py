import sqlite3


def init_db(db_path="app.db"):
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS api_keys (id INTEGER PRIMARY KEY, provider TEXT, key_value TEXT)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS token_usage (id INTEGER PRIMARY KEY, key_id INTEGER, tokens INTEGER, date TEXT)"
        )



def get_db_conn(db_path="app.db"):
    return sqlite3.connect(db_path)
