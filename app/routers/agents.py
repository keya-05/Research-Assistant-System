import logging
from app.auth import verify_token
from fastapi import APIRouter, Depends, HTTPException
from app.database import SessionLocal
from app.models import Agent
from pydantic import BaseModel

router = APIRouter(
    prefix="/agents",
    tags=["agents"],
)

logger = logging.getLogger(__name__)


class AgentCreate(BaseModel):
    name: str
    agent_type: str
    status: str


@router.post("/")
def create_agent(agent_data: AgentCreate, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        new_agent = Agent(
            name=agent_data.name,
            type=agent_data.agent_type,
            status=agent_data.status,
        )
        db.add(new_agent)
        db.commit()
        db.refresh(new_agent)

        logger.info(
            "Created agent %s (id=%s) type=%s status=%s",
            new_agent.name,
            new_agent.id,
            new_agent.type,
            new_agent.status,
        )
        return {
            "id": new_agent.id,
            "name": new_agent.name,
            "type": new_agent.type,
            "status": new_agent.status,
        }
    except Exception:
        db.rollback()
        logger.exception(
            "Failed to create agent %s type=%s status=%s",
            agent_data.name,
            agent_data.agent_type,
            agent_data.status,
        )
        raise
    finally:
        db.close()


@router.get("/")
def get_agents(dep=Depends(verify_token), status: str = None, limit: int = 10, offset: int = 0):
    db = SessionLocal()
    try:
        query = db.query(Agent)
        if status:
            query = query.filter(Agent.status == status)
        agents = query.offset(offset).limit(limit).all()
        return agents
    finally:
        db.close()


@router.get("/{agent_id}")
def get_agent(agent_id: int, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        logger.info("Retrieving agent with id=%s", agent_id)
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            logger.warning("Agent id=%s not found", agent_id)
            raise HTTPException(status_code=404, detail="agent not found")
        logger.info(
            "Found agent %s (id=%s) type=%s status=%s",
            agent.name,
            agent.id,
            agent.type,
            agent.status,
        )
        return agent
    finally:
        db.close()

# UPDATE AGENT STATUS


@router.put("/{agent_id}")
def update_agent(agent_id: int, status: str, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        agent = db.query(Agent).filter(Agent.id == agent_id).first()

        if not agent:
            logger.warning("Agent id=%s not found for status update", agent_id)
            raise HTTPException(status_code=404, detail="agent not found")

        old_status = agent.status
        try:
            agent.status = status
            db.commit()
        except Exception:
            db.rollback()
            raise
        logger.info(
            "Updated agent %s (id=%s) status %s -> %s",
            agent.name,
            agent.id,
            old_status,
            status,
        )
        return {"message": "Updated successfully"}
    finally:
        db.close()


@router.delete("/{agent_id}")
def delete_agent(agent_id: int, dep=Depends(verify_token)):
    db = SessionLocal()
    try:
        logger.info("Deleting agent with id=%s", agent_id)
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            logger.warning("Agent id=%s not found", agent_id)
            raise HTTPException(status_code=404, detail="agent not found")
        db.delete(agent)
        db.commit()
        logger.info("Deleted agent %s (id=%s)", agent.name, agent.id)
        return {"message": "Deleted successfully"}
    except Exception:
        db.rollback()
        logger.exception("Failed to delete agent id=%s", agent_id)
        raise
    finally:
        db.close()
