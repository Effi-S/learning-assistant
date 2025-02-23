from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pacer.models.file_model import FileEntry


class ProjectBase(BaseModel):
    id: UUID
    name: str


class ProjectData(ProjectBase):
    data: Optional[dict] = None
    files: list[FileEntry] = Field(default_factory=list)

    class Config:
        from_attributes = True  # Enables ORM support
