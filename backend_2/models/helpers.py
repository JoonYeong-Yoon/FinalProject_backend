# JSON 처리 및 SQL 실행에 필요한 모듈 import
import json
from sqlalchemy import text
from sqlalchemy.engine import Connection


# -----------------------------
# SQL UPDATE 문에서 SET 절 생성 함수
# -----------------------------
def build_set_clause(fields: dict):
    """
    fields 딕셔너리를 기반으로 UPDATE용 set_clause 생성
    예: {'name': 'John', 'age': 30} -> "name = :name, age = :age"
    """
    return ", ".join([f"{k} = :{k}" for k in fields.keys()])


# -----------------------------
# JSON 필드 처리 함수
# -----------------------------
def handle_json_fields(fields: dict, json_keys: list):
    """
    특정 키들을 JSON 문자열로 변환
    """
    for key in json_keys:
        if key in fields:
            fields[key] = json.dumps(fields[key] or [])


# -----------------------------
# 공통 UPDATE 처리 함수
# -----------------------------
def update_record(
    db: Connection,
    table: str,
    user_id: int,
    fields: dict,
    json_keys=None,
    insert_func=None
):
    json_keys = json_keys or []
    handle_json_fields(fields, json_keys)

    # ⭐ 1. 반드시 초기화
    existing = None

    # ⭐ 2. SELECT (존재 여부 확인)
    stmt = text(f"SELECT * FROM {table} WHERE user_id = :uid")
    print("stmt:", stmt)

    try:
        existing = db.execute(stmt, {"uid": user_id}).mappings().first()
    except Exception as e:
        print("SELECT 오류:", e)
        db.rollback()   # ⭐ 중요

    print("existing:", existing)

    # ⭐ 3. 없으면 INSERT
    if not existing:
        if insert_func:
            try:
                insert_func(db, user_id, **fields)
                db.commit()
            except Exception as e:
                print("INSERT 오류:", e)
                db.rollback()
        return

    # ⭐ 4. 있으면 UPDATE
    set_clause = build_set_clause(fields)
    fields["user_id"] = user_id

    update_stmt = text(
        f"UPDATE {table} SET {set_clause} WHERE user_id = :user_id"
    )

    try:
        db.execute(update_stmt, fields)
        db.commit()
    except Exception as e:
        print("UPDATE 오류:", e)
        db.rollback()
