from datetime import timedelta

from fastapi import HTTPException
from sqlmodel import Session

from app.core import security
from app.core.config import settings
from app.core.security import get_password_hash, verify_password
from app.models import User
from app.repositories import user_repo
from app.schemas import Message, NewPassword, Token, UserUpdate
from app.utils import (
    generate_password_reset_token,
    generate_reset_password_email,
    send_email,
    verify_password_reset_token,
)

# Dummy hash to use for timing attack prevention when user is not found
DUMMY_HASH = "$argon2id$v=19$m=65536,t=3,p=4$MjQyZWE1MzBjYjJlZTI0Yw$YTU4NGM5ZTZmYjE2NzZlZjY0ZWY3ZGRkY2U2OWFjNjk"


def authenticate_user(*, session: Session, email: str, password: str) -> User | None:
    """
    Authenticate a user by email and password, with defense against timing attacks
    and auto password hash upgrade.
    """
    db_user = user_repo.get_user_by_email(session=session, email=email)
    if not db_user:
        verify_password(password, DUMMY_HASH)
        return None

    verified, updated_password_hash = verify_password(password, db_user.hashed_password)
    if not verified:
        return None

    if updated_password_hash:
        user_repo.update_user(
            session=session,
            db_user=db_user,
            user_in=UserUpdate(),
            hashed_password=updated_password_hash,
        )
    return db_user


def create_access_token_for_user(*, user: User) -> Token:
    """
    Generate JWT access token for a user.
    """
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    return Token(
        access_token=security.create_access_token(
            user.id, expires_delta=access_token_expires
        )
    )


def recover_password_service(*, session: Session, email: str) -> Message:
    """
    Send password recovery email to user if they exist (without revealing existence info).
    """
    user = user_repo.get_user_by_email(session=session, email=email)
    if user:
        password_reset_token = generate_password_reset_token(email=email)
        email_data = generate_reset_password_email(
            email_to=user.email, email=email, token=password_reset_token
        )
        send_email(
            email_to=user.email,
            subject=email_data.subject,
            html_content=email_data.html_content,
        )
    return Message(
        message="If that email is registered, we sent a password recovery link"
    )


def reset_password_service(*, session: Session, body: NewPassword) -> Message:
    """
    Verify token and update user password.
    """
    email = verify_password_reset_token(token=body.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid token")

    user = user_repo.get_user_by_email(session=session, email=email)
    if not user:
        raise HTTPException(status_code=400, detail="Invalid token")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    hashed_password = get_password_hash(body.new_password)
    user_repo.update_user(
        session=session,
        db_user=user,
        user_in=UserUpdate(),
        hashed_password=hashed_password,
    )
    return Message(message="Password updated successfully")
