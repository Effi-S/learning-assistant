import base64
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileStatus, FileType


class FileEntryBase(BaseModel):
    """Pydantic model for FileEntry"""

    id: UUID = None
    filepath: str
    type_: FileType = Field(default=FileType.AUTO, alias="type")


class FileEntry(FileEntryBase):
    title: str = Field(None, repr=False)
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

    def model_post_init(self, *args, **kwargs):
        if self.type_ == FileType.AUTO:
            self.type_ = FileType.from_suffix(Path(self.filepath).suffix)
        self.title = self.data.get("title", self.filepath)
        if self.type_ == FileType.URL:
            self.title = f"[{self.title}]({self.filepath})"

    class Config:
        from_attributes = True  # Enable ORM support


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
