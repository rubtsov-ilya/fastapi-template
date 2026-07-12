import uuid

from sqlmodel import Session, col, func, select

from app.models import User
from app.schemas import UserCreate, UserUpdate


def get_user_by_id(*, session: Session, user_id: uuid.UUID) -> User | None:
    return session.get(User, user_id)


def get_user_by_email(*, session: Session, email: str) -> User | None:
    statement = select(User).where(User.email == email)
    return session.exec(statement).first()


def get_users_paginated(
    *, session: Session, skip: int = 0, limit: int = 100
) -> list[User]:
    statement = (
        select(User).order_by(col(User.created_at).desc()).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())


def count_users(*, session: Session) -> int:
    count_statement = select(func.count()).select_from(User)
    return session.exec(count_statement).one()


def create_user(
    *, session: Session, user_create: UserCreate, hashed_password: str
) -> User:
    db_obj = User.model_validate(
        user_create, update={"hashed_password": hashed_password}
    )
    session.add(db_obj)
    session.commit()
    session.refresh(db_obj)
    return db_obj


def update_user(
    *,
    session: Session,
    db_user: User,
    user_in: UserUpdate,
    hashed_password: str | None = None,
) -> User:
    user_data = user_in.model_dump(exclude_unset=True)
    extra_data = {}
    if hashed_password is not None:
        extra_data["hashed_password"] = hashed_password

    # Remove password if it was passed as plain text in user_data,
    # since we handle the hashed version separately
    user_data.pop("password", None)

    db_user.sqlmodel_update(user_data, update=extra_data)
    session.add(db_user)
    session.commit()
    session.refresh(db_user)
    return db_user


def delete_user(*, session: Session, db_user: User) -> None:
    session.delete(db_user)
    session.commit()
