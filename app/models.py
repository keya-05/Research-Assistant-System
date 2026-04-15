from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
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


class Feedback(Base):
    """
    Model for storing human feedback on agent classifications.
    This is the core of RLHF: each record captures the agent's prediction,
    the human's correction, and a reward score.
    """
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, nullable=False)
    original_text = Column(Text)  # Snapshot of the ticket text

    # Agent's original classification
    agent_category = Column(String)
    agent_urgency = Column(String)

    # Human expert's correction
    correct_category = Column(String)
    correct_urgency = Column(String)
    was_correct = Column(Boolean, default=False)
    correction_reason = Column(Text, nullable=True)

    # Reward signal
    reward_score = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
