from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TagInResponse(BaseModel):
    id: int
    name: str
    color: str
    created_at: datetime

    class Config:
        from_attributes = True


class TicketBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)


class TicketCreate(TicketBase):
    tag_ids: Optional[List[int]] = None


class TicketUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    status: Optional[str] = None
    tag_ids: Optional[List[int]] = None


class TicketResponse(TicketBase):
    id: int
    status: str
    tags: List[TagInResponse]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
