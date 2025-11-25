# SQLAlchemy의 text 모듈 import
# 문자열 기반 SQL 문을 실행할 때 사용
from sqlalchemy import text

# -----------------------------
# 구독 상태 업데이트 함수
# -----------------------------
def set_subscription(db, email: str, subscribed: bool):
    """
    users 테이블에서 특정 사용자의 구독 상태(is_subscribed)를 업데이트
    - db: SQLAlchemy DB 연결 객체
    - email: 구독 상태를 변경할 사용자 이메일
    - subscribed: True이면 구독 시작, False이면 구독 취소
    """
    # 1. UPDATE SQL 실행
    # email을 기준으로 해당 사용자의 is_subscribed 컬럼 값을 변경
    db.execute(
        text("UPDATE testing.users SET is_subscribed = :s WHERE email = :email"),
        {"email": email, "s": subscribed}  # 바인딩 파라미터
    )

    # 2. 변경사항 DB 커밋
    db.commit()
