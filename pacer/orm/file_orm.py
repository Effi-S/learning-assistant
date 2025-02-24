import uuid
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import JSON, UUID, Column, ForeignKey, Integer, Null, String, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class FileStatus(StrEnum):
    CREATED = "Created"
    SUMMARY_CREATED = "Created Summary"
    PROCESSED = "processed"
    FAILED = "failed"


class File(Base):
    __tablename__ = "files"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    filepath = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Text, default=str(FileStatus.CREATED), nullable=True)
    data = Column(JSON, default=Null, nullable=True)

    project_ref = relationship("Project", back_populates="files")
