import uuid

from sqlalchemy import UUID, VARCHAR, Column, ForeignKey, Null, Text
from sqlalchemy.orm import relationship

from pacer.orm.base import Base


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(
        UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    project_id = Column(UUID(as_uuid=False), ForeignKey("projects.id"), nullable=False)
    type = Column(VARCHAR, nullable=False)
    category = Column(VARCHAR, default=Null, nullable=True)
    content = Column(Text, default="", nullable=False)
    project_ref = relationship("Project", back_populates="chat_messages")
