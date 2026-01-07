"""
Factual memory using SQL database.
Stores leads, contacts, notes, and structured interaction history.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager
from typing import Optional, List
from datetime import datetime, timezone
import uuid

from config import settings
from models import Base, Lead, Note, Interaction, EscalationEvent, LeadStatus, LeadSource
from observability import trace_logger


class FactualMemory:
    """SQL-based factual memory for CRM data."""

    def __init__(self, database_url: str = None):
        """Initialize factual memory with database connection."""
        self.database_url = database_url or settings.database_url
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False} if "sqlite" in self.database_url else {}
        )
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Get database session context manager."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            trace_logger.error_occurred(
                error_type="database_error",
                error_message=str(e)
            )
            raise
        finally:
            session.close()

    def create_lead(
        self,
        email: str,
        name: Optional[str] = None,
        source: str = "website_form",
        metadata: dict = None
    ) -> Lead:
        """Create a new lead."""
        with self.get_session() as session:
            lead = Lead(
                id=str(uuid.uuid4()),
                email=email,
                name=name,
                source=LeadSource(source),
                status=LeadStatus.NEW,
                metadata=metadata or {},
                created_at=datetime.now(timezone.utc)
            )
            session.add(lead)
            session.commit()
            session.refresh(lead)

            trace_logger.memory_updated(
                memory_type="factual",
                lead_id=lead.id,
                operation="create_lead",
                email=email
            )

            return lead

    def get_lead_by_email(self, email: str) -> Optional[Lead]:
        """Get lead by email."""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.email == email).first()
            if lead:
                # Detach from session to use outside context
                session.expunge(lead)
            return lead

    def get_lead_by_id(self, lead_id: str) -> Optional[Lead]:
        """Get lead by ID."""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if lead:
                session.expunge(lead)
            return lead

    def update_lead(self, lead_id: str, **kwargs) -> Optional[Lead]:
        """Update lead fields."""
        with self.get_session() as session:
            lead = session.query(Lead).filter(Lead.id == lead_id).first()
            if not lead:
                return None

            for key, value in kwargs.items():
                if hasattr(lead, key):
                    setattr(lead, key, value)

            session.commit()
            session.refresh(lead)
            session.expunge(lead)

            trace_logger.memory_updated(
                memory_type="factual",
                lead_id=lead_id,
                operation="update_lead",
                fields=list(kwargs.keys())
            )

            return lead

    def add_note(
        self,
        lead_id: str,
        content: str,
        note_type: str = "general",
        created_by: str = "agent"
    ) -> Note:
        """Add a note to a lead."""
        with self.get_session() as session:
            note = Note(
                lead_id=lead_id,
                content=content,
                note_type=note_type,
                created_by=created_by,
                created_at=datetime.now(timezone.utc)
            )
            session.add(note)
            session.commit()
            session.refresh(note)
            session.expunge(note)

            trace_logger.memory_updated(
                memory_type="factual",
                lead_id=lead_id,
                operation="add_note",
                note_type=note_type
            )

            return note

    def add_interaction(
        self,
        lead_id: str,
        message_from: str,
        message_text: str,
        decision_type: Optional[str] = None,
        confidence_score: Optional[float] = None,
        tools_used: List[str] = None,
        sources_retrieved: List[str] = None
    ) -> Interaction:
        """Record an interaction."""
        with self.get_session() as session:
            interaction = Interaction(
                lead_id=lead_id,
                message_from=message_from,
                message_text=message_text,
                decision_type=decision_type,
                confidence_score=confidence_score,
                tools_used=tools_used or [],
                sources_retrieved=sources_retrieved or [],
                created_at=datetime.now(timezone.utc)
            )
            session.add(interaction)
            session.commit()
            session.refresh(interaction)
            session.expunge(interaction)

            trace_logger.memory_updated(
                memory_type="factual",
                lead_id=lead_id,
                operation="add_interaction",
                message_from=message_from
            )

            return interaction

    def get_lead_interactions(
        self,
        lead_id: str,
        limit: int = 10
    ) -> List[Interaction]:
        """Get recent interactions for a lead."""
        with self.get_session() as session:
            interactions = (
                session.query(Interaction)
                .filter(Interaction.lead_id == lead_id)
                .order_by(Interaction.created_at.desc())
                .limit(limit)
                .all()
            )
            # Detach from session
            for interaction in interactions:
                session.expunge(interaction)
            return interactions

    def create_escalation(
        self,
        lead_id: str,
        reason: str,
        confidence_score: float,
        context: dict = None
    ) -> EscalationEvent:
        """Create an escalation event."""
        with self.get_session() as session:
            escalation = EscalationEvent(
                lead_id=lead_id,
                reason=reason,
                confidence_score=confidence_score,
                context=context or {},
                created_at=datetime.now(timezone.utc)
            )
            session.add(escalation)
            session.commit()
            session.refresh(escalation)
            session.expunge(escalation)

            trace_logger.escalation_triggered(
                reason=reason,
                confidence=confidence_score,
                context=context or {}
            )

            return escalation

    def get_leads_for_followup(self) -> List[Lead]:
        """Get leads that need follow-up."""
        with self.get_session() as session:
            now = datetime.now(timezone.utc)
            leads = (
                session.query(Lead)
                .filter(
                    Lead.next_followup_at.isnot(None),
                    Lead.next_followup_at <= now,
                    Lead.status.in_([LeadStatus.CONTACTED, LeadStatus.QUALIFIED])
                )
                .all()
            )
            for lead in leads:
                session.expunge(lead)
            return leads
