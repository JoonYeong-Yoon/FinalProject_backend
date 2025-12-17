# subscription 관련 DB 모델 함수 import
# set_subscription: users 테이블의 is_subscribed 컬럼 업데이트
from models.subscription_model import set_subscription

# 구독 시작 함수
# email: 구독할 사용자의 이메일
# db: SQLAlchemy DB 세션/연결 객체
def start_subscription(email, db):
    # DB에서 해당 사용자의 is_subscribed를 True로 변경
    set_subscription(db, email, True)
    # 구독 시작 성공 메시지 반환
    return {"message": "구독을 시작했습니다!"}

# 구독 취소 함수
# email: 구독 취소할 사용자의 이메일
# db: SQLAlchemy DB 세션/연결 객체
def cancel_subscription(email, db):
    # DB에서 해당 사용자의 is_subscribed를 False로 변경
    set_subscription(db, email, False)
    # 구독 취소 성공 메시지 반환
    return {"message": "구독이 취소되었습니다!"}
