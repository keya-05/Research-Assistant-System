import logging
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from app.auth import verify_token
from app.database import SessionLocal
from app.models import Ticket
from app.rate_limiter import limiter
from app.services.tickets import (
    apply_ticket_filters,
    apply_ticket_sort,
    classify_ticket,
    create_escalation_log,
    filter_tickets_by_sla,
    get_ticket_stats,
    search_tickets as search_ticket_records,
    serialize_ticket,
)

router = APIRouter(
    prefix="/tickets",
    tags=["tickets"],
)

logger = logging.getLogger(__name__)


class TicketCategory(str, Enum):
    billing = "Billing"
    technical = "Technical"
    general = "General"


class TicketUrgency(str, Enum):
    high = "High"
    medium = "Medium"
    low = "Low"


class TicketStatus(str, Enum):
    open = "open"
    needs_review = "needs_review"
    approved = "approved"
    closed = "closed"


class TicketSort(str, Enum):
    newest = "newest"
    oldest = "oldest"
    urgency = "urgency"


class TicketCreate(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)
    email: str = Field(..., min_length=3, max_length=320)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("text must not be empty")
        return cleaned

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if "@" not in cleaned or "." not in cleaned.split("@")[-1]:
            raise ValueError("email must be a valid email address")
        return cleaned


class TicketResponse(BaseModel):
    id: int
    text: str
    email: str
    category: TicketCategory
    urgency: TicketUrgency
    status: str
    draft_reply: str | None
    created_at: str
    sla_due_at: str
    sla_breached: bool


class TicketReviewUpdate(BaseModel):
    category: TicketCategory | None = None
    urgency: TicketUrgency | None = None
    draft_reply: str | None = None
    status: TicketStatus = TicketStatus.approved

    @field_validator("draft_reply")
    @classmethod
    def validate_draft_reply(cls, value: str | None) -> str | None:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("draft_reply must not be empty")
        return cleaned


class TicketStatsResponse(BaseModel):
    total: int
    high_priority: int
    pending_review: int
    billing: int
    escalated: int
    breached: int


def _serialize_ticket(ticket: Ticket) -> TicketResponse:
    return TicketResponse(**serialize_ticket(ticket))


@router.post("/", response_model=TicketResponse)
@limiter.limit("5/minute")
async def create_ticket(request: Request, ticket_data: TicketCreate, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        classification = await classify_ticket(ticket_data.text)
        new_ticket = Ticket(
            text=ticket_data.text,
            email=ticket_data.email,
            category=classification["category"],
            urgency=classification["urgency"],
            status=TicketStatus.needs_review.value,
            draft_reply=classification["draft_reply"],
        )
        db.add(new_ticket)
        db.flush()
        create_escalation_log(db, new_ticket)
        db.commit()
        db.refresh(new_ticket)

        logger.info(
            "Created ticket id=%s email=%s category=%s urgency=%s status=%s",
            new_ticket.id,
            new_ticket.email,
            new_ticket.category,
            new_ticket.urgency,
            new_ticket.status,
        )
        return _serialize_ticket(new_ticket)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to create ticket for %s", ticket_data.email)
        raise HTTPException(
            status_code=500,
            detail="Unable to create the ticket right now. Please try again shortly.",
        )
    finally:
        db.close()


@router.get("/", response_model=list[TicketResponse])
def get_tickets(
    request: Request,
    dep=Depends(verify_token),
    category: TicketCategory | None = None,
    urgency: TicketUrgency | None = None,
    status: TicketStatus | None = None,
    sla_breached: bool | None = None,
    sort_by: TicketSort = TicketSort.newest,
):
    db = SessionLocal()
    try:
        query = db.query(Ticket)
        query = apply_ticket_filters(
            query,
            category.value if category else None,
            urgency.value if urgency else None,
            status.value if status else None,
        )
        query = apply_ticket_sort(query, sort_by.value)
        tickets = filter_tickets_by_sla(query.all(), sla_breached)
        return [_serialize_ticket(ticket) for ticket in tickets]
    except Exception:
        logger.exception("Failed to load tickets")
        raise HTTPException(
            status_code=500,
            detail="Unable to load tickets right now. Please refresh and try again.",
        )
    finally:
        db.close()


@router.get("/review", response_model=list[TicketResponse])
def get_review_tickets(request: Request, dep=Depends(verify_token), sla_breached: bool | None = None):
    db = SessionLocal()
    try:
        query = db.query(Ticket).filter(Ticket.status == TicketStatus.needs_review.value)
        tickets = filter_tickets_by_sla(
            apply_ticket_sort(query, TicketSort.urgency.value).all(),
            sla_breached,
        )
        return [_serialize_ticket(ticket) for ticket in tickets]
    except Exception:
        logger.exception("Failed to load tickets for review")
        raise HTTPException(
            status_code=500,
            detail="Unable to load the review queue right now. Please try again.",
        )
    finally:
        db.close()


@router.get("/search", response_model=list[TicketResponse])
@limiter.limit("20/minute")
def search_tickets(
    request: Request,
    q: str,
    dep=Depends(verify_token),
    sla_breached: bool | None = None,
):
    db = SessionLocal()
    try:
        if not q.strip():
            raise HTTPException(status_code=400, detail="Search query cannot be empty.")
        tickets = filter_tickets_by_sla(search_ticket_records(db, q), sla_breached)
        return [_serialize_ticket(ticket) for ticket in tickets]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to search tickets for query=%s", q)
        raise HTTPException(
            status_code=500,
            detail="Unable to search tickets right now. Please try again.",
        )
    finally:
        db.close()


@router.get("/stats", response_model=TicketStatsResponse)
def ticket_stats(request: Request, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        return TicketStatsResponse(**get_ticket_stats(db))
    except Exception:
        logger.exception("Failed to load ticket stats")
        raise HTTPException(
            status_code=500,
            detail="Unable to load dashboard stats right now. Please try again.",
        )
    finally:
        db.close()


@router.patch("/{ticket_id}/review", response_model=TicketResponse)
@limiter.limit("15/minute")
def review_ticket(
    request: Request,
    ticket_id: int,
    review_data: TicketReviewUpdate,
    dep=Depends(verify_token),
):
    db = SessionLocal()
    try:
        ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found.")

        if review_data.category is not None:
            ticket.category = review_data.category.value
        if review_data.urgency is not None:
            ticket.urgency = review_data.urgency.value
        if review_data.draft_reply is not None:
            ticket.draft_reply = review_data.draft_reply

        ticket.status = review_data.status.value
        db.commit()
        db.refresh(ticket)

        logger.info(
            "Reviewed ticket id=%s category=%s urgency=%s status=%s",
            ticket.id,
            ticket.category,
            ticket.urgency,
            ticket.status,
        )
        return _serialize_ticket(ticket)
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        logger.exception("Failed to review ticket id=%s", ticket_id)
        raise HTTPException(
            status_code=500,
            detail="Unable to update the ticket review right now. Please try again.",
        )
    finally:
        db.close()
