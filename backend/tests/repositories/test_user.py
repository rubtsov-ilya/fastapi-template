from fastapi.encoders import jsonable_encoder
from sqlmodel import Session

from app.core.security import get_password_hash
from app.repositories import user_repo
from app.schemas import UserCreate, UserUpdate
from tests.utils.utils import random_email, random_lower_string


def test_create_user(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    assert user.email == email
    assert hasattr(user, "hashed_password")


def test_check_if_user_is_active(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    assert user.is_active is True


def test_check_if_user_is_active_inactive(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_active=False)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    assert user.is_active is False


def test_check_if_user_is_superuser(db: Session) -> None:
    email = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    assert user.is_superuser is True


def test_check_if_user_is_superuser_normal_user(db: Session) -> None:
    username = random_email()
    password = random_lower_string()
    user_in = UserCreate(email=username, password=password)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    assert user.is_superuser is False


def test_get_user(db: Session) -> None:
    password = random_lower_string()
    username = random_email()
    user_in = UserCreate(email=username, password=password, is_superuser=True)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    user_2 = user_repo.get_user_by_id(session=db, user_id=user.id)
    assert user_2
    assert user.email == user_2.email
    assert jsonable_encoder(user) == jsonable_encoder(user_2)


def test_update_user(db: Session) -> None:
    password = random_lower_string()
    email = random_email()
    user_in = UserCreate(email=email, password=password, is_superuser=True)
    hashed_password = get_password_hash(password)
    user = user_repo.create_user(
        session=db, user_create=user_in, hashed_password=hashed_password
    )
    new_password = random_lower_string()
    user_in_update = UserUpdate(password=new_password, is_superuser=True)
    if user.id is not None:
        new_hashed_password = get_password_hash(new_password)
        user_repo.update_user(
            session=db,
            db_user=user,
            user_in=user_in_update,
            hashed_password=new_hashed_password,
        )
    user_2 = user_repo.get_user_by_id(session=db, user_id=user.id)
    assert user_2
    assert user.email == user_2.email
    from app.core.security import verify_password

    verified, _ = verify_password(new_password, user_2.hashed_password)
    assert verified
