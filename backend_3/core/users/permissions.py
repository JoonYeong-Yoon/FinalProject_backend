from fastapi import Depends

from core.users.security import ROLE_SCOPES
from core.users.exceptions import ForbiddenException


def require_scopes(required_scopes: list[str]):
    def dependency(current_user=Depends()):
        role = current_user.get("role")
        
        if role not in ROLE_SCOPES:
            raise ForbiddenException("잘못된 권한 정보입니다.")
        
        user_scopes = ROLE_SCOPES.get(role, [])

        for scope in required_scopes:
            if scope not in user_scopes:
                raise ForbiddenException()

        return current_user

    return dependency
