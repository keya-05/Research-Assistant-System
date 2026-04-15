from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from app.database import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    email = Column(String, nullable=False, index=True)
    category = Column(String, nullable=False, index=True)
    urgency = Column(String, nullable=False)
    status = Column(String, nullable=False, default="open")
    draft_reply = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class EscalationLog(Base):
    __tablename__ = "escalation_logs"

    id = Column(Integer, primary_key=True, index=True)
    ticket_id = Column(String, nullable=False, index=True)
    conversation = Column(Text, nullable=True)
    escalate = Column(String, nullable=False, default="false")
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
