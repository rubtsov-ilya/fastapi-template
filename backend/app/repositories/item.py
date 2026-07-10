import uuid

from sqlmodel import Session, select, col, func

from app.models import Item
from app.schemas import ItemCreate, ItemUpdate


def get_item_by_id(*, session: Session, item_id: uuid.UUID) -> Item | None:
    return session.get(Item, item_id)


def get_items_paginated(*, session: Session, skip: int = 0, limit: int = 100) -> list[Item]:
    statement = (
        select(Item).order_by(col(Item.created_at).desc()).offset(skip).limit(limit)
    )
    return list(session.exec(statement).all())


def count_items(*, session: Session) -> int:
    count_statement = select(func.count()).select_from(Item)
    return session.exec(count_statement).one()


def get_items_by_owner_paginated(
    *, session: Session, owner_id: uuid.UUID, skip: int = 0, limit: int = 100
) -> list[Item]:
    statement = (
        select(Item)
        .where(Item.owner_id == owner_id)
        .order_by(col(Item.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    return list(session.exec(statement).all())


def count_items_by_owner(*, session: Session, owner_id: uuid.UUID) -> int:
    count_statement = (
        select(func.count())
        .select_from(Item)
        .where(Item.owner_id == owner_id)
    )
    return session.exec(count_statement).one()


def create_item(*, session: Session, item_in: ItemCreate, owner_id: uuid.UUID) -> Item:
    db_item = Item.model_validate(item_in, update={"owner_id": owner_id})
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def update_item(*, session: Session, db_item: Item, item_in: ItemUpdate) -> Item:
    update_dict = item_in.model_dump(exclude_unset=True)
    db_item.sqlmodel_update(update_dict)
    session.add(db_item)
    session.commit()
    session.refresh(db_item)
    return db_item


def delete_item(*, session: Session, db_item: Item) -> None:
    session.delete(db_item)
    session.commit()
