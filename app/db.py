from contextlib import contextmanager
from typing import Generator

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

_db_pool = None


def init_db_pool(database_url: str, minconn: int = 1, maxconn: int = 10) -> None:
    global _db_pool
    if _db_pool is None:
        _db_pool = pool.SimpleConnectionPool(minconn, maxconn, dsn=database_url)


def close_db_pool() -> None:
    global _db_pool
    if _db_pool is not None:
        _db_pool.closeall()
        _db_pool = None


@contextmanager
def get_db() -> Generator[psycopg2.extensions.connection, None, None]:
    if _db_pool is None:
        raise RuntimeError("Database pool has not been initialized")

    conn = _db_pool.getconn()
    try:
        yield conn
    finally:
        _db_pool.putconn(conn)


def get_cursor(conn: psycopg2.extensions.connection) -> RealDictCursor:
    return conn.cursor(cursor_factory=RealDictCursor)
