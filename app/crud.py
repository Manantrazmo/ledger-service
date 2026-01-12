from sqlalchemy.orm import Session
from .database import DBUser
from .models import UserCreate
from .auth import get_password_hash

def get_user(db: Session, user_id: int):
    return db.query(DBUser).filter(DBUser.id == user_id).first()

def get_user_by_email(db: Session, email: str):
    return db.query(DBUser).filter(DBUser.email == email).first()

def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(DBUser).offset(skip).limit(limit).all()

def create_user(db: Session, user: UserCreate, is_superuser: bool = False):
    hashed_password = get_password_hash(user.password)
    db_user = DBUser(
        email=user.email, 
        hashed_password=hashed_password,
        is_superuser=is_superuser,
        is_active=is_superuser # Superuser active by default
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def update_user_status(db: Session, user_id: int, is_active: bool):
    db_user = db.query(DBUser).filter(DBUser.id == user_id).first()
    if db_user:
        db_user.is_active = is_active
        db.commit()
        db.refresh(db_user)
    return db_user
