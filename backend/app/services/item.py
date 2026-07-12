import uuid

from fastapi import HTTPException
from sqlmodel import Session

from app.models import Item, User
from app.repositories import item_repo
from app.schemas import ItemCreate, ItemUpdate


def get_item_service(
    *, session: Session, current_user: User, item_id: uuid.UUID
) -> Item:
    """
    Get item by ID with ownership validation.
    """
    item = item_repo.get_item_by_id(session=session, item_id=item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    if not current_user.is_superuser and (item.owner_id != current_user.id):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return item


def create_item_service(
    *, session: Session, item_in: ItemCreate, owner_id: uuid.UUID
) -> Item:
    """
    Create new item.
    """
    return item_repo.create_item(session=session, item_in=item_in, owner_id=owner_id)


def update_item_service(
    *, session: Session, current_user: User, item_id: uuid.UUID, item_in: ItemUpdate
) -> Item:
    """
    Update an item with ownership validation.
    """
    item = get_item_service(session=session, current_user=current_user, item_id=item_id)
    return item_repo.update_item(session=session, db_item=item, item_in=item_in)


def delete_item_service(
    *, session: Session, current_user: User, item_id: uuid.UUID
) -> None:
    """
    Delete an item with ownership validation.
    """
    item = get_item_service(session=session, current_user=current_user, item_id=item_id)
    item_repo.delete_item(session=session, db_item=item)
