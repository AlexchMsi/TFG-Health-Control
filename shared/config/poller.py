"""
ConfigPoller — polls the /config/targets API every N seconds.

Each agent instantiates one ConfigPoller, which dynamically adds and removes
APScheduler jobs without requiring a container restart.  Codex (or any HTTP
client) can POST/DELETE targets and the agent picks up the change within one
poll cycle (default 30 s).

Usage:
    poller = ConfigPoller(
        api_url="http://api:8000",
        agent_type="siemens",
        scheduler=my_agent_scheduler,
        poll_every=30,
    )
    poller.start()   # registers the sync job; runs immediately then every N s
"""

import logging
from typing import Protocol

import requests
from apscheduler.schedulers.base import BaseScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class AgentSchedulerProtocol(Protocol):
    """Minimal interface expected from agent schedulers."""

    def add_target(self, target: dict) -> None: ...
    def remove_target(self, target_id: str) -> None: ...


class ConfigPoller:
    def __init__(
        self,
        api_url: str,
        agent_type: str,
        scheduler: AgentSchedulerProtocol,
        aps_scheduler: BaseScheduler,
        poll_every: int = 30,
    ) -> None:
        self._api_url = api_url.rstrip("/")
        self._agent_type = agent_type
        self._scheduler = scheduler
        self._aps = aps_scheduler
        self._poll_every = poll_every
        self._known_ids: set[str] = set()

    def start(self) -> None:
        self._sync()  # immediate first run
        self._aps.add_job(
            self._sync,
            trigger=IntervalTrigger(seconds=self._poll_every),
            id="config_poller",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(
            "ConfigPoller started — polling /config/targets?agent_type=%s every %ds",
            self._agent_type,
            self._poll_every,
        )

    def _sync(self) -> None:
        try:
            resp = requests.get(
                f"{self._api_url}/config/targets",
                params={"agent_type": self._agent_type},
                timeout=10,
            )
            resp.raise_for_status()
            targets: list[dict] = resp.json()
        except Exception as exc:
            logger.warning("ConfigPoller: failed to fetch targets — %s", exc)
            return

        active_ids = {t["id"] for t in targets if t["enabled"]}

        for target in targets:
            if target["enabled"] and target["id"] not in self._known_ids:
                logger.info("ConfigPoller: adding target %s", target["id"])
                self._scheduler.add_target(target)
                self._known_ids.add(target["id"])

        for removed_id in self._known_ids - active_ids:
            logger.info("ConfigPoller: removing target %s", removed_id)
            self._scheduler.remove_target(removed_id)
            self._known_ids.discard(removed_id)
