import uuid
from enum import StrEnum
from typing import Optional

from pydantic import BaseModel
from sqlalchemy import JSON, UUID, Column, ForeignKey, Integer, Null, String, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base

_suffix_map = {}


class FileStatus(StrEnum):
    CREATED = "Created"
    SUMMARY_CREATED = "Created Summary"
    PROCESSED = "processed"
    FAILED = "failed"


class FileType(StrEnum):
    """
    Register a suffix by by giving a tuple, e.g:
        TEXT = ("text", ".txt", ".md")
        will register ".txt" and ".md" as the suffixes for text
    """

    AUTO = "auto"
    TEXT = ("text", ".txt")
    PDF = ("pdf", ".pdf")
    PYTHON = ("python", ".py")
    JSON = ("json", ".json")
    MARKDOWN = ("markdown", ".md")
    URL = "URL"

    def __new__(cls, value, *suffixes):
        obj = str.__new__(cls, value)
        obj._value_ = value
        obj.suffix = suffixes[0] if suffixes else None
        for suffix in suffixes:
            _suffix_map[suffix] = value
        return obj

    @classmethod
    def from_suffix(cls, suffix):
        return cls(_suffix_map.get(suffix, cls.URL))


class File(Base):
    __tablename__ = "files"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    type = Column(Text, default=FileType.TEXT, nullable=False)
    filepath = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    status = Column(Text, default=str(FileStatus.CREATED), nullable=True)
    data = Column(JSON, default=dict)

    project_ref = relationship("Project", back_populates="files")
