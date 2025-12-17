# 기본 틀입니다. 수정하지 말아주시면 감사하겠습니다.
# 컨트롤러는 API 주고 받을 때 상태만을 기재하는 곳입니다.
from fastapi.responses import JSONResponse
from fastapi import status

from services import ai
async def say_hello():
    try:
        res = ai.get_hello_message()
        return JSONResponse(    
            {"message":res},
            status_code=status.HTTP_200_OK
        )
    except Exception:
        return JSONResponse(
            {"message":"테스트 실패"},
            status_code=status.HTTP_404_NOT_FOUND
        )