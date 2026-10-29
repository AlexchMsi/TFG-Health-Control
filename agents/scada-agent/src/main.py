import logging
import os
import signal
import sys
import time

from shared.config.poller import ConfigPoller
from shared.config.settings import Settings
from shared.influx.writer import InfluxWriter
from shared.utils.logging import configure_logging

from .scheduler import AgentScheduler


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("SCADA agent starting...")

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
        agent_type="scada",
        scheduler=scheduler,
        aps_scheduler=scheduler.aps,
        poll_every=30,
    )
    poller.start()

    def _shutdown(signum, frame):
        logger.info("SCADA agent shutting down (signal %d)...", signum)
        scheduler.shutdown()
        writer.close()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    logger.info("SCADA agent running — waiting for targets from %s", api_url)
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
