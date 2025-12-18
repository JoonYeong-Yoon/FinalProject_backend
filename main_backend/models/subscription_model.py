# SQLAlchemy의 text 모듈 import
# 문자열 기반 SQL 문을 실행할 때 사용
from sqlalchemy import text
from sqlalchemy.engine import Connection
from datetime import datetime

# tables에 정의된 db의 테이블 불러오기
from .tables import SUBSCRIPTION_TABLE, SUBSCRIPTION_PLAN_TABLE

# -----------------------------
# 구독 상태 업데이트 함수
# -----------------------------
# def set_subscription(db, email: str, subscribed: bool):
#     """
#     users 테이블에서 특정 사용자의 구독 상태(is_subscribed)를 업데이트
#     - db: SQLAlchemy DB 연결 객체
#     - email: 구독 상태를 변경할 사용자 이메일
#     - subscribed: True이면 구독 시작, False이면 구독 취소
#     """
#     # 1. UPDATE SQL 실행
#     # email을 기준으로 해당 사용자의 is_subscribed 컬럼 값을 변경
#     db.execute(
#         text(f"UPDATE {USERS_TABLE} SET is_subscribed = :s WHERE email = :email"),
#         {"email": email, "s": subscribed}  # 바인딩 파라미터
#     )

#     # 2. 변경사항 DB 커밋
#     db.commit()

def set_subscription( user_id: str, plan_name:str, status:str,db: Connection):
    """
    users 테이블에서 특정 사용자의 구독 상태(is_subscribed)를 업데이트
    - db: SQLAlchemy DB 연결 객체
    - email: 구독 상태를 변경할 사용자 이메일
    - subscribed: True이면 구독 시작, False이면 구독 취소
    """
    # plan_name [Basic, Pro, Premium]
    plan_id = db.execute(
        text(f"""
            SELECT id
            FROM {SUBSCRIPTION_PLAN_TABLE}
            WHERE name = :name
        """),
        {"name": plan_name}
    )
    plan_id = plan_id.scalar()
    print("plan_id",plan_id)
    if plan_id is None:
        db.execute(
            text(f"""
                DELETE FROM {SUBSCRIPTION_TABLE}
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
    else:
        sub_id = db.execute(
            text(f"""
                SELECT id
                FROM {SUBSCRIPTION_TABLE}
                WHERE user_id = :user_id
            """),
            {"user_id": user_id}
        )
        sub_id = sub_id.scalar()
        if sub_id:
            print("sub_id",sub_id)
            db.execute(
                text(f"""
                    UPDATE {SUBSCRIPTION_TABLE}
                    SET
                        plan_id = :plan_id,
                        status = :status,
                        start_date = :start_date
                    WHERE id = :sub_id
                """),
                {
                    "sub_id": sub_id,              # 🔥 수정 대상 subscription id
                    "plan_id": plan_id,
                    "status": status,
                    "start_date": datetime.utcnow(),
                }
            )

        else:
            db.execute(
                text(f"""
                    INSERT INTO {SUBSCRIPTION_TABLE} (
                        user_id,
                        plan_id,
                        status,
                        start_date
                    )
                    VALUES (
                        :user_id,
                        :plan_id,
                        :status,
                        :start_date
                    )
                """),
                {
                    "user_id": user_id,
                    "plan_id": plan_id,
                    "status": status,
                    "start_date": datetime.utcnow(),
                }
            )
            print("aaaa")
    # 2. 변경사항 DB 커밋
    db.commit()

def delete_subscription(user_id: str, db: Connection,):
    db.execute(
        text(f"""
            DELETE FROM {SUBSCRIPTION_TABLE}
            WHERE user_id = :user_id
        """),
        {"user_id": user_id}
    )
    db.commit()
