from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from typing import Any

def success(data: Any = None, status_code: int = 200):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": True,
            "data": jsonable_encoder(data)
        }
    )


def error(message: str, status_code: int = 400, code: str | None = None):
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "message": message,
                "code": code
            }
        }
    )
