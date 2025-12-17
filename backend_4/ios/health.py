from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from ios.schemas import HealthData

router = APIRouter(
    prefix="/ios",
    tags=["iOS"]
)

@router.post("/upload")
def upload_health_data(
    data: HealthData,
    db: Session = Depends(get_db)
):
    print("📥 받은 iOS 건강 데이터:", data.dict())

    return {
        "message": "건강 데이터 수신 완료",
        "data": data.dict()
    }
