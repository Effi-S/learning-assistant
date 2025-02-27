from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class ProjectBase(BaseModel):
    id: UUID = None
    name: str


class ProjectData(ProjectBase):
    data: Optional[dict] = Field(default=None, repr=False)

    class Config:
        from_attributes = True  # Enables ORM support
