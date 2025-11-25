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
    - fields: 업데이트할 필드 dict
    - json_keys: JSON 변환할 키 리스트
    예: {"prefer": ["a","b"]} -> {"prefer": '["a","b"]'}
    """
    for key in json_keys:
        if key in fields:
            fields[key] = json.dumps(fields[key] or [])

# -----------------------------
# 공통 UPDATE 처리 함수
# -----------------------------
def update_record(db: Connection, table: str, user_id: int, fields: dict, json_keys=None, insert_func=None):
    """
    DB 테이블에 공통으로 UPDATE 수행
    - db: DB 연결 객체 (Connection)
    - table: 업데이트할 테이블 이름
    - user_id: 대상 사용자 ID
    - fields: 업데이트할 필드 dict
    - json_keys: JSON으로 변환할 필드 리스트
    - insert_func: 레코드가 없을 경우 INSERT 처리 함수
    """
    json_keys = json_keys or []  # None일 경우 빈 리스트로 초기화
    handle_json_fields(fields, json_keys)  # JSON 필드 처리

    # 1. 기존 레코드 존재 여부 확인
    stmt = text(f"SELECT * FROM {table} WHERE user_id = :uid")  # text()로 감싸야 SQLAlchemy 2.x 호환
    existing = db.execute(stmt, {"uid": user_id}).mappings().first()

    # 2. 레코드가 없으면 insert_func 호출
    if not existing:
        if insert_func:
            insert_func(db, user_id, **fields)
        return

    # 3. 기존 레코드가 있으면 UPDATE 수행
    set_clause = build_set_clause(fields)  # "field1 = :field1, field2 = :field2" 형태 생성
    fields["user_id"] = user_id
    update_stmt = text(f"UPDATE {table} SET {set_clause} WHERE user_id = :user_id")  # text() 사용
    db.execute(update_stmt, fields)  # DB에 업데이트 실행
    db.commit()  # 커밋
