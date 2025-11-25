# __init__.py 파일은 패키지 초기화용
# models 패키지를 외부에서 import할 때
# 각 모델별 함수들을 한 곳에서 모아 노출(re-export)하도록 설정

# users_model.py에서 필요한 함수 import
# users 테이블 관련 CRUD 함수
from .users_model import (
    get_user_by_email,  # 이메일로 사용자 조회
    get_user_by_id,     # ID로 사용자 조회
    insert_user,        # 사용자 삽입
    update_user,        # 사용자 정보 업데이트
    delete_user,        # 사용자 삭제
)

# user_info_model.py에서 필요한 함수 import
# user_info 테이블 관련 CRUD 함수
from .user_info_model import (
    get_user_info,      # user_info 조회
    insert_user_info,   # user_info 삽입
    update_user_info,   # user_info 업데이트
)

# user_body_model.py에서 필요한 함수 import
# user_body_info 테이블 관련 CRUD 함수
from .user_body_model import (
    get_body_info,      # user_body_info 조회
    insert_body_info,   # user_body_info 삽입
    update_body_info,   # user_body_info 업데이트
)

# subscription_model.py에서 필요한 함수 import
# users 테이블 is_subscribed 컬럼 관리
from .subscription_model import set_subscription
