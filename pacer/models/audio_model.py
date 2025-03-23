import base64
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from pacer.models.project_model import ProjectData
from pacer.orm.file_orm import FileStatus, FileType


class AudioEntry(BaseModel):
    """Pydantic model for FileEntry"""

    id: UUID = None
    content: bytes = Field(..., repr=False)
    
    class Config:
        from_attributes = True  # Enable ORM support


if __name__ == "__main__":
    import IPython

    IPython.embed(colors="Neutral")
