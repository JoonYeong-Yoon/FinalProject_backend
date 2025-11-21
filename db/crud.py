from sqlalchemy.orm import Session
from models.models import User
from web.services.hashing import password_hash

def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()

def create_user(db: Session, email: str, username: str, password: str):
    new_user = User(
        email=email,
        name=username,
        password_hash=password_hash(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
