"""
Siemens PLC Agent — entry point.

Lifecycle:
1. Read settings from environment (.env via Pydantic BaseSettings)
2. Connect to InfluxDB
3. Start BackgroundScheduler
4. Start ConfigPoller → polls /config/targets?agent_type=siemens every 30 s
5. Block on signal (SIGTERM / SIGINT for graceful shutdown)
"""

import logging
import os
import signal
import sys
import time

from shared.config.settings import Settings
from shared.config.poller import ConfigPoller
from shared.influx.writer import InfluxWriter
from shared.utils.logging import configure_logging

from .scheduler import AgentScheduler


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)

    logger.info("Siemens agent starting...")

    writer = InfluxWriter(
        url=settings.influxdb_url,
        token=settings.influxdb_admin_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
    )

    scheduler = AgentScheduler(writer)
    scheduler.start()

    api_url = os.getenv("API_URL", "http://api:8000")
    poller = ConfigPoller(
        api_url=api_url,
        agent_type="siemens",
        scheduler=scheduler,
        aps_scheduler=scheduler.aps,
        poll_every=30,
    )
    poller.start()

    # Graceful shutdown on SIGTERM (Docker stop) or SIGINT (Ctrl-C)
    def _shutdown(signum, frame):
        logger.info("Siemens agent shutting down (signal %d)...", signum)
        scheduler.shutdown()
        writer.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("Siemens agent running — waiting for targets from %s", api_url)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
