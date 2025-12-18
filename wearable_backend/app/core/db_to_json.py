import sqlite3
import json
import base64


def db_to_json(db_path: str) -> dict:
    """
    SQLite .db 파일을 받아서 내부 모든 테이블을 JSON(dict) 형태로 변환한다.
    bytes(BLOB) 타입은 base64 문자열로 자동 변환한다.
    """

    try:
        conn = sqlite3.connect(db_path)
    except Exception as e:
        raise ValueError(f"DB 파일을 열 수 없습니다: {str(e)}")

    cursor = conn.cursor()

    # 테이블 목록 읽기
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    if not tables:
        conn.close()
        raise ValueError("DB 내부에 테이블이 없습니다.")

    result = {}

    for (table_name,) in tables:
        try:
            cursor.execute(f"SELECT * FROM {table_name};")
            rows = cursor.fetchall()
        except Exception:
            continue

        col_names = [col[0] for col in cursor.description]

        table_rows = []
        for row in rows:
            row_dict = {}
            for col, value in zip(col_names, row):

                # 🔥 bytes(BLOB)를 문자열로 안전하게 변환
                if isinstance(value, bytes):
                    value = base64.b64encode(value).decode("utf-8")

                row_dict[col] = value

            table_rows.append(row_dict)

        result[table_name] = table_rows

    conn.close()

    if not result:
        raise ValueError("DB는 열렸지만 데이터를 읽을 수 없습니다.")

    return result
