import logging

from shared.utils.logging import configure_logging

from .influx_reader import InfluxReader
from .ollama_client import OllamaClient
from .scheduler import RecommendationScheduler
from .settings import Settings


def main() -> None:
    settings = Settings()
    configure_logging(settings.log_level)
    logger = logging.getLogger(__name__)
    logger.info("Recommendation agent starting...")

    reader = InfluxReader(
        url=settings.influxdb_url,
        token=settings.influxdb_admin_token,
        org=settings.influxdb_org,
        bucket=settings.influxdb_bucket,
    )
    ollama = OllamaClient(settings.ollama_url, settings.ollama_model)
    ollama.wait_ready()
    ollama.pull_model()

    scheduler = RecommendationScheduler(
        reader=reader,
        ollama=ollama,
        interval_minutes=settings.analysis_interval_minutes,
        output_path=settings.recommendations_path,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
