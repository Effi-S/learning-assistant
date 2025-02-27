import base64
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileStatus, FileType


class FileEntryBase(BaseModel):
    """Pydantic model for FileEntry"""

    id: UUID = None
    filepath: str
    type_: FileType = FileType.AUTO


class FileEntry(FileEntryBase):
    content: str = Field(..., repr=False)
    status: FileStatus = FileStatus.CREATED
    data: Optional[dict] = Field(default_factory=dict, repr=False)
    project_ref: ProjectData = Field(default=None, repr=False)

    @field_validator("content", mode="before")
    @classmethod
    def convert_bytes_to_str(cls, value: str | bytes) -> str:
        if isinstance(value, bytes):
            return base64.b64encode(value).decode("utf-8")  # Encode to base64
        return value

    class Config:
        from_attributes = True  # Enable ORM support

    @field_validator("type_", mode="before")
    @classmethod
    def convert_bytes_to_str(cls, value: str | bytes) -> str:
        if isinstance(value, bytes):
            return base64.b64encode(value).decode("utf-8")  # Encode to base64
        return value

    class Config:
        from_attributes = True  # Enable ORM support
