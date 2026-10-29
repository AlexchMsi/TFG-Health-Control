import json
import logging
import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from .influx_reader import InfluxReader
from .ollama_client import OllamaClient
from .prompt_builder import build_prompt

logger = logging.getLogger(__name__)


class RecommendationScheduler:
    def __init__(self, reader: InfluxReader, ollama: OllamaClient, interval_minutes: int, output_path: str) -> None:
        self._reader = reader
        self._ollama = ollama
        self._interval_minutes = interval_minutes
        self._output_path = Path(output_path)
        self._latest = deque(maxlen=10)
        self._load_history()
        self._aps = BlockingScheduler(timezone="UTC")

    def start(self) -> None:
        self._aps.add_job(
            func=self.run,
            trigger=IntervalTrigger(minutes=self._interval_minutes),
            id="recommendation_analysis",
            max_instances=1,
            misfire_grace_time=self._interval_minutes * 60,
            replace_existing=True,
        )
        self.run()
        self._aps.start()

    def shutdown(self) -> None:
        self._aps.shutdown(wait=False)

    def run(self) -> None:
        """Job entry point: a failed analysis must never kill the agent."""
        try:
            self.analyze()
        except Exception:
            logger.exception("analysis_failed")

    def analyze(self) -> dict:
        metrics = self._reader.get_latest_metrics()
        raw = self._ollama.generate(build_prompt(metrics))
        result = self._parse(raw)
        result["generated_at"] = datetime.now(timezone.utc).isoformat()
        self._latest.appendleft(result)
        self._write()
        return result

    def _parse(self, raw: str) -> dict:
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {
                "summary": "No se pudo interpretar la respuesta del modelo.",
                "risk_level": "medium",
                "recommendations": [
                    {"priority": "medium", "source_id": "ai", "finding": raw, "action": "Revisar la salida del modelo."}
                ],
            }

    def _load_history(self) -> None:
        """Reload persisted analyses so a container restart keeps the history."""
        try:
            if self._output_path.exists():
                data = json.loads(self._output_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    # File stores newest first; extend preserves that order.
                    self._latest.extend(data[:10])
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("could not reload history from %s: %s", self._output_path, exc)

    def _write(self) -> None:
        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._output_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(list(self._latest), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self._output_path)  # atomic within the same directory
