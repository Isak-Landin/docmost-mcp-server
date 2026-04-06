import os
from contextlib import contextmanager
from typing import Iterator

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.extensions import connection as PgConnection
from psycopg2 import OperationalError


class DocmostConnectionError(Exception):
    pass


def _get_dsn() -> str:
    url = (os.getenv("DOCMOST_DB_URL") or "").strip()
    if url:
        return url
    host = os.getenv("DOCMOST_DB_HOST", "db")
    port = os.getenv("DOCMOST_DB_PORT", "5432")
    dbname = os.getenv("DOCMOST_DB_NAME", "docmost")
    user = os.getenv("DOCMOST_DB_USER", "docmost")
    password = os.getenv("DOCMOST_DB_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


@contextmanager
def get_conn() -> Iterator[PgConnection]:
    conn = None
    try:
        conn = psycopg2.connect(_get_dsn(), cursor_factory=RealDictCursor)
        yield conn
        conn.commit()
    except OperationalError as exc:
        if conn is not None:
            conn.rollback()
        raise DocmostConnectionError("Docmost database connection failed") from exc
    except Exception:
        if conn is not None:
            conn.rollback()
        raise
    finally:
        if conn is not None:
            conn.close()
