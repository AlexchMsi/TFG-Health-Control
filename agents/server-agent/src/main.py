"""
Server Agent entry point.

Reads configuration from /app/config/targets.yaml and environment variables,
then starts the APScheduler polling loop.
"""
import logging
import signal
import sys
from pathlib import Path

import yaml

from shared.config.settings import Settings
from shared.influx.writer import InfluxWriter
from shared.utils.logging import configure_logging

from .scheduler import AgentScheduler

logger = logging.getLogger(__name__)

CONFIG_PATH = Path("/app/config/targets.yaml")


def load_config(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)

    logger.info("server_agent_starting version=1.0.0")

    writer = InfluxWriter(
        url=settings.influxdb_url,
        token=settings.influxdb_admin_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
    )

    config = load_config(CONFIG_PATH)
    scheduler = AgentScheduler(config, writer)

    def _shutdown(signum, frame):
        logger.info("server_agent_stopping signal=%d", signum)
        scheduler.shutdown()
        writer.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        writer.close()
        logger.info("server_agent_stopped")


if __name__ == "__main__":
    main()
