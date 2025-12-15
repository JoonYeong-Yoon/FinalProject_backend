from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    username: str      # 🔥 name → username 변경
    password: str

class UserOut(BaseModel):
    email: str
    username: str      # 🔥 동일하게 username으로 반환

    class Config:
        orm_mode = True

class Login(BaseModel):
    email: str
    password: str