import uuid

from sqlalchemy import JSON, UUID, Column, Null, String
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class Project(Base):
    __tablename__ = "projects"
    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name = Column(String, unique=False, nullable=False)
    data = Column(JSON, default=Null, nullable=True)
    files = relationship(
        "File", back_populates="project_ref", cascade="all, delete-orphan"
    )
