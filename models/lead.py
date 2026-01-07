"""
SQLAlchemy models for CRM (factual memory).
Represents leads, contacts, notes, and interaction history.
"""

from datetime import datetime, timezone
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Integer, Float, DateTime, Text, JSON, ForeignKey, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class LeadStatus(str, PyEnum):
    """Lead status enum."""
    NEW = "new"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    UNQUALIFIED = "unqualified"
    MEETING_SCHEDULED = "meeting_scheduled"
    PROPOSAL_SENT = "proposal_sent"
    WON = "won"
    LOST = "lost"
    ESCALATED = "escalated"


class LeadSource(str, PyEnum):
    """Lead source enum."""
    WEBSITE_FORM = "website_form"
    EMAIL = "email"
    PHONE = "phone"
    REFERRAL = "referral"
    SOCIAL_MEDIA = "social_media"
    OTHER = "other"


class Lead(Base):
    """Lead model representing a prospective customer."""

    __tablename__ = "leads"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    company = Column(String(255))
    phone = Column(String(50))

    status = Column(
        Enum(LeadStatus),
        default=LeadStatus.NEW,
        nullable=False,
        index=True
    )
    source = Column(
        Enum(LeadSource),
        default=LeadSource.WEBSITE_FORM,
        nullable=False
    )

    # Qualification scoring
    qualification_score = Column(Float, default=0.0)
    budget_range = Column(String(100))
    timeline = Column(String(100))
    decision_maker = Column(String(255))

    # Metadata
    metadata = Column(JSON, default=dict)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    last_contacted_at = Column(DateTime(timezone=True))
    next_followup_at = Column(DateTime(timezone=True))

    # Relationships
    notes = relationship("Note", back_populates="lead", cascade="all, delete-orphan")
    interactions = relationship(
        "Interaction",
        back_populates="lead",
        cascade="all, delete-orphan",
        order_by="Interaction.created_at.desc()"
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "company": self.company,
            "phone": self.phone,
            "status": self.status.value if self.status else None,
            "source": self.source.value if self.source else None,
            "qualification_score": self.qualification_score,
            "budget_range": self.budget_range,
            "timeline": self.timeline,
            "decision_maker": self.decision_maker,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_contacted_at": self.last_contacted_at.isoformat() if self.last_contacted_at else None,
            "next_followup_at": self.next_followup_at.isoformat() if self.next_followup_at else None,
        }


class Note(Base):
    """Notes associated with a lead."""

    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="general")  # general, qualification, technical, etc.
    created_by = Column(String(100), default="agent")  # agent or human
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # Relationships
    lead = relationship("Lead", back_populates="notes")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "content": self.content,
            "note_type": self.note_type,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Interaction(Base):
    """Interaction history with a lead."""

    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False)

    # Message content
    message_from = Column(String(50), nullable=False)  # lead or agent
    message_text = Column(Text, nullable=False)

    # Agent decision metadata
    decision_type = Column(String(50))  # retrieve, reason_only, use_tool, clarify, escalate
    confidence_score = Column(Float)
    tools_used = Column(JSON, default=list)
    sources_retrieved = Column(JSON, default=list)

    # Timestamps
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    # Relationships
    lead = relationship("Lead", back_populates="interactions")

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "message_from": self.message_from,
            "message_text": self.message_text,
            "decision_type": self.decision_type,
            "confidence_score": self.confidence_score,
            "tools_used": self.tools_used,
            "sources_retrieved": self.sources_retrieved,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class EscalationEvent(Base):
    """Track escalation events to humans."""

    __tablename__ = "escalation_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    lead_id = Column(String(36), ForeignKey("leads.id"), nullable=False)

    reason = Column(Text, nullable=False)
    confidence_score = Column(Float)
    context = Column(JSON, default=dict)

    resolved = Column(String(20), default="pending")  # pending, resolved, ignored
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(String(100))

    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )

    def to_dict(self):
        """Convert to dictionary."""
        return {
            "id": self.id,
            "lead_id": self.lead_id,
            "reason": self.reason,
            "confidence_score": self.confidence_score,
            "context": self.context,
            "resolved": self.resolved,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
