import uuid

from sqlalchemy import UUID, Column, ForeignKey, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class Note(Base):
    __tablename__ = "notes"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    content = Column(Text, default="", nullable=False)
    project_ref = relationship("Project", back_populates="notes")
