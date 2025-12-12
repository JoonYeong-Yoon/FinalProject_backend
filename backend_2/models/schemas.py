from pydantic import BaseModel

class UserCreate(BaseModel):
    email: str
    password: str
    name: str
    goal: str | None = None
