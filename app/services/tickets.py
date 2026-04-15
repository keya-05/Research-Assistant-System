import json
import logging
import os
import re
from datetime import UTC, datetime, timedelta

import httpx
from dotenv import load_dotenv
from sqlalchemy import case, func, or_
from sqlalchemy.orm import Session

from app.models import EscalationLog, Ticket

load_dotenv()

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")

VALID_CATEGORIES = {"Billing", "Technical", "General"}
VALID_URGENCY = {"High", "Medium", "Low"}
HIGH_URGENCY_KEYWORDS = {
    "down",
    "outage",
    "urgent",
    "critical",
    "severe",
    "breach",
    "security",
    "fraud",
    "charged twice",
    "double charged",
    "payment failed repeatedly",
    "cannot access account",
    "locked out",
    "service unavailable",
    "production",
}
MEDIUM_URGENCY_KEYWORDS = {
    "slow",
    "delay",
    "issue",
    "problem",
    "error",
    "bug",
    "not working",
    "unable to",
    "failed",
}
FALLBACK_CLASSIFICATION = {
    "category": "General",
    "urgency": "Low",
    "draft_reply": (
        "Thank you for contacting support. We have received your ticket and "
        "a team member will review it shortly."
    ),
}
HIGH_PRIORITY_REASON = "High urgency detected"
SLA_HOURS = {
    "High": 1,
    "Medium": 4,
    "Low": 24,
}


def _extract_llm_json(content: str) -> dict:
    cleaned = content.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if len(lines) >= 3:
            cleaned = "\n".join(lines[1:-1]).strip()
    data = json.loads(cleaned)
    if not isinstance(data, dict):
        raise ValueError("LLM response was not a JSON object")
    return data


def _normalize_category(value: str | None) -> str:
    candidate = (value or "").strip().title()
    if candidate not in VALID_CATEGORIES:
        return "General"
    return candidate


def _normalize_urgency(value: str | None) -> str:
    candidate = (value or "").strip().title()
    if candidate not in VALID_URGENCY:
        return "Low"
    return candidate


def normalize_classification(result: dict) -> dict:
    draft_reply = str(result.get("draft_reply") or "").strip()
    if not draft_reply:
        draft_reply = FALLBACK_CLASSIFICATION["draft_reply"]

    normalized = {
        "category": _normalize_category(result.get("category")),
        "urgency": _normalize_urgency(result.get("urgency")),
        "draft_reply": draft_reply,
    }
    logger.info("LLM output normalized to %s", normalized)
    return normalized


def contains_keyword(text: str, keyword: str) -> bool:
    if " " in keyword:
        return keyword in text
    return re.search(rf"\b{re.escape(keyword)}\b", text) is not None


def calibrate_urgency(text: str, predicted_urgency: str) -> str:
    lowered = text.lower()

    if any(contains_keyword(lowered, keyword) for keyword in HIGH_URGENCY_KEYWORDS):
        return "High"

    if predicted_urgency == "High":
        if any(contains_keyword(lowered, keyword) for keyword in MEDIUM_URGENCY_KEYWORDS):
            return "Medium"
        return "Low"

    return predicted_urgency


async def classify_ticket(text: str, db: Session = None) -> dict:
    if not OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not configured, using fallback classification")
        return FALLBACK_CLASSIFICATION.copy()

    # Step 1: Build dynamic learning context (RLHF)
    dynamic_context = ""
    if db:
        try:
            context = get_agent_context(db)
            dynamic_context = build_dynamic_prompt_section(context)
        except Exception as e:
            logger.warning("Failed to build learning context: %s", e)

    system_content = "You are a support triage assistant. Respond with JSON only."
    if dynamic_context:
        system_content += f"\n\n--- AGENT MEMORY & LEARNING CONTEXT ---\n{dynamic_context}"

    prompt = (
        "You classify support tickets.\n"
        "Return only valid JSON with keys category, urgency, and draft_reply.\n"
        "Allowed category values: Billing, Technical, General.\n"
        "Allowed urgency values: High, Medium, Low.\n"
        "Use this urgency rubric strictly:\n"
        "- High: service outage, security risk, fraud, repeated billing impact, account lockout, production issue, or issue blocking core use.\n"
        "- Medium: degraded performance, recurring bug, partial feature failure, or issue affecting use but not a full outage.\n"
        "- Low: general question, minor inconvenience, feature request, or non-blocking issue.\n"
        "Do not choose High unless the ticket clearly indicates serious business impact or an urgent blocking problem.\n"
        "draft_reply should be a short professional first response to the customer.\n"
        "Ticket text:\n"
        f"{text}"
    )

    try:
        async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": OPENROUTER_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": system_content,
                        },
                        {"role": "user", "content": prompt},
                    ],
                },
            )
            response.raise_for_status()

        payload = response.json()
        content = payload["choices"][0]["message"]["content"]
        raw_result = _extract_llm_json(content)
        logger.info("Raw LLM output: %s", raw_result)
        normalized = normalize_classification(raw_result)
        normalized["urgency"] = calibrate_urgency(text, normalized["urgency"])
        logger.info("Urgency calibrated to %s", normalized["urgency"])
        return normalized
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError) as exc:
        logger.exception("Falling back after ticket classification failure")
        fallback = FALLBACK_CLASSIFICATION.copy()
        fallback["draft_reply"] = (
            "Thank you for contacting support. The ticket was stored and queued for manual review."
        )
        logger.info("Fallback classification used because of %s", exc)
        return fallback


def serialize_ticket(ticket: Ticket) -> dict:
    sla_due_at = calculate_sla_due_at(ticket)
    sla_breached = is_sla_breached(ticket, sla_due_at=sla_due_at)
    return {
        "id": ticket.id,
        "text": ticket.text,
        "email": ticket.email,
        "category": ticket.category,
        "urgency": ticket.urgency,
        "status": ticket.status,
        "draft_reply": ticket.draft_reply,
        "created_at": ticket.created_at.isoformat(),
        "sla_due_at": sla_due_at.isoformat(),
        "sla_breached": sla_breached,
    }


def calculate_sla_due_at(ticket: Ticket) -> datetime:
    hours = SLA_HOURS.get(ticket.urgency, SLA_HOURS["Low"])
    return ticket.created_at + timedelta(hours=hours)


def is_sla_breached(ticket: Ticket, *, sla_due_at: datetime | None = None) -> bool:
    if ticket.status in {"approved", "closed"}:
        return False

    if sla_due_at is None:
        sla_due_at = calculate_sla_due_at(ticket)

    now = datetime.now(UTC).replace(tzinfo=None)
    return now > sla_due_at


def create_escalation_log(db: Session, ticket: Ticket) -> None:
    should_escalate = ticket.urgency == "High"
    if not should_escalate:
        return

    log = EscalationLog(
        ticket_id=str(ticket.id),
        conversation=ticket.text,
        escalate="true",
        reason=HIGH_PRIORITY_REASON,
    )
    db.add(log)
    db.flush()


def urgency_rank_expression():
    return case(
        (Ticket.urgency == "High", 3),
        (Ticket.urgency == "Medium", 2),
        else_=1,
    )


def apply_ticket_filters(query, category: str | None, urgency: str | None, status: str | None):
    if category:
        query = query.filter(Ticket.category == category)
    if urgency:
        query = query.filter(Ticket.urgency == urgency)
    if status:
        query = query.filter(Ticket.status == status)
    return query


def apply_ticket_sort(query, sort_by: str | None):
    if sort_by == "urgency":
        return query.order_by(urgency_rank_expression().desc(), Ticket.created_at.desc())
    if sort_by == "oldest":
        return query.order_by(Ticket.created_at.asc())
    return query.order_by(Ticket.created_at.desc())


def search_tickets(db: Session, query_text: str):
    term = f"%{query_text.strip()}%"
    query = db.query(Ticket).filter(
        or_(Ticket.text.ilike(term), Ticket.email.ilike(term), Ticket.draft_reply.ilike(term))
    )
    return query.order_by(Ticket.created_at.desc()).all()


def filter_tickets_by_sla(tickets: list[Ticket], sla_breached: bool | None) -> list[Ticket]:
    if sla_breached is None:
        return tickets
    return [ticket for ticket in tickets if is_sla_breached(ticket) == sla_breached]


def get_ticket_stats(db: Session) -> dict:
    tickets = db.query(Ticket).all()
    total = len(tickets)
    high_priority = sum(1 for ticket in tickets if ticket.urgency == "High")
    pending_review = sum(1 for ticket in tickets if ticket.status == "needs_review")
    billing = sum(1 for ticket in tickets if ticket.category == "Billing")
    breached = sum(1 for ticket in tickets if is_sla_breached(ticket))
    escalated = db.query(func.count(EscalationLog.id)).filter(EscalationLog.escalate == "true").scalar() or 0
    return {
        "total": total,
        "high_priority": high_priority,
        "pending_review": pending_review,
        "billing": billing,
        "escalated": escalated,
        "breached": breached,
    }
