from pydantic import BaseModel, Field

class UserCreate(BaseModel):
    email: str
    password: str
    username: str = Field(..., description="사용자 이름")


class UserUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    age: int | None = None
