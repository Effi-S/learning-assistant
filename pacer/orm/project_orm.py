import uuid

from sqlalchemy import JSON, UUID, Column, Null, String
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String, unique=True, nullable=False)
    data = Column(JSON, default=dict)
    files = relationship(
        "File", back_populates="project_ref", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", back_populates="project_ref", cascade="all, delete-orphan"
    )
    code_cells = relationship(
        "CodeCell", back_populates="project_ref", cascade="all, delete-orphan"
    )
