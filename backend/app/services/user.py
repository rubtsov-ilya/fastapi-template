from fastapi import HTTPException
from sqlmodel import Session

from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User
from app.repositories import user_repo
from app.schemas import UpdatePassword, UserCreate, UserUpdate, UserUpdateMe
from app.utils import generate_new_account_email, send_email


def create_user_service(*, session: Session, user_in: UserCreate) -> User:
    """
    Business logic for creating a new user (with email uniqueness check, password hashing, and email sending).
    """
    user = user_repo.get_user_by_email(session=session, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )

    hashed_password = get_password_hash(user_in.password)
    user = user_repo.create_user(
        session=session, user_create=user_in, hashed_password=hashed_password
    )

    if settings.emails_enabled and user_in.email:
        email_data = generate_new_account_email(
            email_to=user_in.email, username=user_in.email, password=user_in.password
        )
        send_email(
            email_to=user_in.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return user


def update_user_service(
    *, session: Session, db_user: User, user_in: UserUpdate
) -> User:
    """
    Business logic for updating a user.
    """
    if user_in.email:
        existing_user = user_repo.get_user_by_email(
            session=session, email=user_in.email
        )
        if existing_user and existing_user.id != db_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    hashed_password = None
    if user_in.password:
        hashed_password = get_password_hash(user_in.password)

    return user_repo.update_user(
        session=session,
        db_user=db_user,
        user_in=user_in,
        hashed_password=hashed_password,
    )


def update_user_me_service(
    *, session: Session, current_user: User, user_in: UserUpdateMe
) -> User:
    """
    Business logic for updating current user's profile.
    """
    if user_in.email:
        existing_user = user_repo.get_user_by_email(
            session=session, email=user_in.email
        )
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409, detail="User with this email already exists"
            )

    user_data = user_in.model_dump(exclude_unset=True)
    current_user.sqlmodel_update(user_data)
    session.add(current_user)
    session.commit()
    session.refresh(current_user)
    return current_user


def update_password_me_service(
    *, session: Session, current_user: User, body: UpdatePassword
) -> None:
    """
    Business logic for updating own password.
    """
    verified, _ = verify_password(body.current_password, current_user.hashed_password)
    if not verified:
        raise HTTPException(status_code=400, detail="Incorrect password")
    if body.current_password == body.new_password:
        raise HTTPException(
            status_code=400, detail="New password cannot be the same as the current one"
        )
    hashed_password = get_password_hash(body.new_password)
    current_user.hashed_password = hashed_password
    session.add(current_user)
    session.commit()
