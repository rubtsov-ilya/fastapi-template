import uuid
from typing import Any

from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.schemas import ItemCreate, ItemPublic, ItemsPublic, ItemUpdate, Message
from app.repositories import item_repo
from app.services import (
    get_item_service,
    create_item_service,
    update_item_service,
    delete_item_service,
)

router = APIRouter(prefix="/items", tags=["items"])


@router.get("/", response_model=ItemsPublic)
def read_items(
    session: SessionDep, current_user: CurrentUser, skip: int = 0, limit: int = 100
) -> Any:
    """
    Retrieve items.
    """
    if current_user.is_superuser:
        count = item_repo.count_items(session=session)
        items = item_repo.get_items_paginated(session=session, skip=skip, limit=limit)
    else:
        count = item_repo.count_items_by_owner(session=session, owner_id=current_user.id)
        items = item_repo.get_items_by_owner_paginated(
            session=session, owner_id=current_user.id, skip=skip, limit=limit
        )

    items_public = [ItemPublic.model_validate(item) for item in items]
    return ItemsPublic(data=items_public, count=count)


@router.get("/{id}", response_model=ItemPublic)
def read_item(session: SessionDep, current_user: CurrentUser, id: uuid.UUID) -> Any:
    """
    Get item by ID.
    """
    return get_item_service(session=session, current_user=current_user, item_id=id)


@router.post("/", response_model=ItemPublic)
def create_item(
    *, session: SessionDep, current_user: CurrentUser, item_in: ItemCreate
) -> Any:
    """
    Create new item.
    """
    return create_item_service(session=session, item_in=item_in, owner_id=current_user.id)


@router.put("/{id}", response_model=ItemPublic)
def update_item(
    *,
    session: SessionDep,
    current_user: CurrentUser,
    id: uuid.UUID,
    item_in: ItemUpdate,
) -> Any:
    """
    Update an item.
    """
    return update_item_service(
        session=session, current_user=current_user, item_id=id, item_in=item_in
    )


@router.delete("/{id}")
def delete_item(
    session: SessionDep, current_user: CurrentUser, id: uuid.UUID
) -> Message:
    """
    Delete an item.
    """
    delete_item_service(session=session, current_user=current_user, item_id=id)
    return Message(message="Item deleted successfully")
