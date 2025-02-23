from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileStatus


class FileEntryBase(BaseModel):
    """Pydantic model for FileEntry"""

    id: UUID
    filepath: str


class FileEntry(FileEntryBase):
    content: str
    status: FileStatus = FileStatus.CREATED
    data: Optional[dict] = None
    project_ref: ProjectData

    class Config:
        from_attributes = True  # Enable ORM support
