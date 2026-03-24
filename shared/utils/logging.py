import logging
import sys


def configure_logging(level: str = "INFO") -> None:
    """Configure structured JSON-like logging for all agents."""
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-8s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%SZ",
    )
    # Silence noisy third-party loggers
    logging.getLogger("pysnmp").setLevel(logging.WARNING)
    logging.getLogger("pyVmomi").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
