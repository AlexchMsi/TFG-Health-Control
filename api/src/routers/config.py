import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from ..database import get_session
from ..models.target import Target, TargetCreate, TargetRead, TargetUpdate

router = APIRouter()


def _to_read(t: Target) -> TargetRead:
    return TargetRead(
        id=t.id,
        plant=t.plant,
        agent_type=t.agent_type,
        display_name=t.display_name,
        enabled=t.enabled,
        config=json.loads(t.config),
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


@router.post("/targets", response_model=TargetRead, status_code=201,
             summary="Register a new monitoring target (called by Codex or manually)")
def create_target(payload: TargetCreate, session: Session = Depends(get_session)):
    if session.get(Target, payload.id):
        raise HTTPException(status_code=409, detail=f"Target '{payload.id}' already exists")
    target = Target(
        id=payload.id,
        plant=payload.plant,
        agent_type=payload.agent_type,
        display_name=payload.display_name,
        enabled=payload.enabled,
        config=json.dumps(payload.config),
    )
    session.add(target)
    session.commit()
    session.refresh(target)
    return _to_read(target)


@router.get("/targets", response_model=list[TargetRead],
            summary="List targets (agents poll this endpoint)")
def list_targets(
    agent_type: Optional[str] = Query(default=None, description="Filter by agent type"),
    session: Session = Depends(get_session),
):
    stmt = select(Target)
    if agent_type:
        stmt = stmt.where(Target.agent_type == agent_type)
    targets = session.exec(stmt).all()
    return [_to_read(t) for t in targets]


@router.get("/targets/{target_id}", response_model=TargetRead,
            summary="Get a single target by ID")
def get_target(target_id: str, session: Session = Depends(get_session)):
    target = session.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found")
    return _to_read(target)


@router.put("/targets/{target_id}", response_model=TargetRead,
            summary="Update a target's config or enabled state")
def update_target(
    target_id: str,
    payload: TargetUpdate,
    session: Session = Depends(get_session),
):
    target = session.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found")

    if payload.plant is not None:
        target.plant = payload.plant
    if payload.display_name is not None:
        target.display_name = payload.display_name
    if payload.enabled is not None:
        target.enabled = payload.enabled
    if payload.config is not None:
        target.config = json.dumps(payload.config)

    target.updated_at = datetime.now(timezone.utc)
    session.add(target)
    session.commit()
    session.refresh(target)
    return _to_read(target)


@router.delete("/targets/{target_id}", status_code=204,
               summary="Remove a target — agent stops collecting within one poll cycle")
def delete_target(target_id: str, session: Session = Depends(get_session)):
    target = session.get(Target, target_id)
    if not target:
        raise HTTPException(status_code=404, detail=f"Target '{target_id}' not found")
    session.delete(target)
    session.commit()
