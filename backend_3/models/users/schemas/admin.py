from pydantic import BaseModel, Field
from typing import Literal


# =========================
# 관리자 권한 변경 요청
# =========================
class AdminRoleUpdate(BaseModel):
    role: Literal["admin", "user"] = Field(
        ...,
        description="변경할 사용자 권한"
    )


# =========================
# 관리자 구독 상태 변경 요청
# =========================
class AdminSubscriptionUpdate(BaseModel):
    is_subscribed: bool = Field(
        ...,
        description="구독 활성화 여부"
    )
