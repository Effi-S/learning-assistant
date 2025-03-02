import uuid

from sqlalchemy import UUID, VARCHAR, Column, ForeignKey, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class CodeCell(Base):
    __tablename__ = "code_cells"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    markdown = Column(Text, default="", nullable=True)
    language = Column(VARCHAR, default="python", nullable=False)
    code = Column(Text, default="", nullable=False)
    output = Column(Text, default="", nullable=True)
    project_ref = relationship("Project", back_populates="code_cells")
