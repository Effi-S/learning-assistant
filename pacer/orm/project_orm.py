import uuid
from datetime import datetime as dt
from datetime import timezone

from sqlalchemy import JSON, UUID, Column, DateTime, String
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String, unique=True, nullable=False)
    data = Column(JSON, default=dict)
    created_at = Column(
        DateTime(timezone=True), default=lambda: dt.now(timezone.utc), nullable=False
    )
    files = relationship(
        "File", back_populates="project_ref", cascade="all, delete-orphan"
    )
    notes = relationship(
        "Note", back_populates="project_ref", cascade="all, delete-orphan"
    )
    jupyter_cells = relationship(
        "JupyterCell", back_populates="project_ref", cascade="all, delete-orphan"
    )
    chat_messages = relationship(
        "ChatMessage", back_populates="project_ref", cascade="all, delete-orphan"
    )
