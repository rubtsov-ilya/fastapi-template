import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


# Shared properties
class ItemBase(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class ItemsPublic(BaseModel):
    data: list[ItemPublic]
    count: int
