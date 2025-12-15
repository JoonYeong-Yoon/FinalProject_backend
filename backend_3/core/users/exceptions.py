from fastapi import HTTPException


class AppException(HTTPException):
    def __init__(self, status_code: int, message: str, code: str | None = None):
        super().__init__(
            status_code=status_code,
            detail={
                "success": False,
                "error": {
                    "message": message,
                    "code": code
                }
            }
        )


class ForbiddenException(AppException):
    def __init__(self, message="접근 권한이 없습니다."):
        super().__init__(403, message, "FORBIDDEN")


class NotFoundException(AppException):
    def __init__(self, message="리소스를 찾을 수 없습니다."):
        super().__init__(404, message, "NOT_FOUND")


class BadRequestException(AppException):
    def __init__(self, message="잘못된 요청입니다."):
        super().__init__(400, message, "BAD_REQUEST")
