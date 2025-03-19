import uuid
from enum import StrEnum, auto

from sqlalchemy import UUID, VARCHAR, Column, ForeignKey, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class CellType(StrEnum):
    PYTHON: str = auto()
    MARKDOWN: str = auto()
    OUTPUT: str = auto()


class JupyterCell(Base):
    __tablename__ = "jupyter_cells"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    type = Column(VARCHAR, default=str(CellType.PYTHON), nullable=False)
    content = Column(Text, default="", nullable=True)
    project_ref = relationship("Project", back_populates="jupyter_cells")
