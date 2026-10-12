"""Request-scoped connections and a small, explicit SQLite DB-API adapter.

Routes retain the original MySQL parameter style. SQLite is for the local demo;
MySQL uses mysql.connector directly, including real transactions and procedures.
"""

import sqlite3
from pathlib import Path

import mysql.connector
from flask import current_app, g


class SQLiteCursor:
    def __init__(self, connection, dictionary=False):
        self.cursor = connection.cursor()
        self.dictionary = dictionary

    def execute(self, sql, params=()):
        sql = sql.replace("%s", "?")
        self.cursor.execute(sql, params)
        return self

    def executemany(self, sql, rows):
        self.cursor.executemany(sql.replace("%s", "?"), rows)

    def fetchall(self):
        rows = self.cursor.fetchall()
        return [dict(row) if self.dictionary else tuple(row) for row in rows]

    def fetchone(self):
        row = self.cursor.fetchone()
        if row is None:
            return None
        return dict(row) if self.dictionary else tuple(row)

    @property
    def lastrowid(self):
        return self.cursor.lastrowid

    @property
    def rowcount(self):
        return self.cursor.rowcount

    def close(self):
        self.cursor.close()


class SQLiteConnection:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.raw = sqlite3.connect(path, timeout=15)
        self.raw.row_factory = sqlite3.Row
        self.raw.execute("PRAGMA foreign_keys = ON")

    def cursor(self, dictionary=False):
        return SQLiteCursor(self.raw, dictionary)

    def start_transaction(self, isolation_level=None):
        self.raw.execute("BEGIN IMMEDIATE")

    def commit(self):
        self.raw.commit()

    def rollback(self):
        self.raw.rollback()

    def close(self):
        self.raw.close()


def connect():
    cfg = current_app.config
    if cfg["DATABASE_BACKEND"] == "sqlite":
        return SQLiteConnection(cfg["DATABASE_PATH"])
    kwargs = dict(
        host=cfg["DB_HOST"],
        port=cfg["DB_PORT"],
        user=cfg["DB_USER"],
        password=cfg["DB_PASSWORD"],
        database=cfg["DB_NAME"],
        charset="utf8mb4",
        connection_timeout=10,
        use_pure=True,
    )
    if cfg.get("DB_UNIX_SOCKET"):
        kwargs["unix_socket"] = cfg["DB_UNIX_SOCKET"]
    return mysql.connector.connect(**kwargs)


def get_db():
    if "db" not in g:
        g.db = connect()
    return g.db


def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        # Roll back abandoned writes, even after a handled exception.
        db.rollback()
        db.close()


def query(sql, params=(), *, one=False):
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(sql, params)
        return cursor.fetchone() if one else cursor.fetchall()
    finally:
        cursor.close()


def execute(sql, params=()):
    cursor = get_db().cursor()
    try:
        cursor.execute(sql, params)
        return cursor.lastrowid, cursor.rowcount
    finally:
        cursor.close()
