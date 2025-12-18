# app/core/db.py
"""
DB 연결 유틸리티 (psycopg2)
- 간단한 get_db_connection 제공 (conn은 호출자가 close/commit 담당)
"""
import psycopg2
from psycopg2 import OperationalError
from core.config import POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD, DB_HOST, DB_PORT

def get_db_connection():
    """
    psycopg2 connection 반환.
    호출자에서 conn.cursor(), commit(), close()를 관리해야 함.
    """
    try:
        conn = psycopg2.connect(
            dbname=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASSWORD,
            host=DB_HOST,
            port=DB_PORT,
        )
        return conn
    except OperationalError as e:
        raise ConnectionError(f"Postgres 연결 실패: {e}")
