from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    color = Column(String(7), default='#6B7280', nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    tickets = relationship('Ticket', secondary='ticket_tags', back_populates='tags')
