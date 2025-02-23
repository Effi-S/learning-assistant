from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    id: UUID
    name: str


class ProjectData(ProjectBase):
    data: Optional[dict] = None

    class Config:
        from_attributes = True  # Enables ORM support
