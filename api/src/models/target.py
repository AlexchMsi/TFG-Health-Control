from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


class Target(SQLModel, table=True):
    id: str = Field(primary_key=True, description="Unique target identifier, e.g. 'planta-valencia-plc-01'")
    plant: str = Field(description="Plant or site name, e.g. 'Valencia'")
    agent_type: str = Field(description="Agent type: 'siemens' | 'rockwell' | 'server' | 'network'")
    display_name: str = Field(description="Human-readable name shown in Grafana / Codex UI")
    enabled: bool = Field(default=True)
    config: str = Field(description="Protocol-specific config serialized as JSON")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ── Request / Response schemas ─────────────────────────────────────────────────

class TargetCreate(SQLModel):
    id: str
    plant: str
    agent_type: str
    display_name: str
    enabled: bool = True
    config: dict  # Codex sends a dict; we serialize to JSON before storing


class TargetUpdate(SQLModel):
    plant: Optional[str] = None
    display_name: Optional[str] = None
    enabled: Optional[bool] = None
    config: Optional[dict] = None


class TargetRead(SQLModel):
    id: str
    plant: str
    agent_type: str
    display_name: str
    enabled: bool
    config: dict  # deserialized back to dict for API responses
    created_at: datetime
    updated_at: datetime
