from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
from influxdb_client.client.exceptions import InfluxDBError

logger = logging.getLogger(__name__)


class WriteError(Exception):
    """Raised when a write to InfluxDB fails."""


class InfluxWriter:
    """
    Single point of contact with InfluxDB for all agents.
    Uses SYNCHRONOUS write mode so errors surface immediately in the polling loop.
    """

    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._write_api = self._client.write_api(write_options=SYNCHRONOUS)
        self._org = org
        self._bucket = bucket

    def write_point(
        self,
        measurement: str,
        tags: dict[str, str],
        fields: dict[str, Any],
        timestamp: datetime | None = None,
    ) -> None:
        """Write a single data point. timestamp defaults to now (UTC)."""
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        point = Point(measurement)
        for key, value in tags.items():
            if value is not None:
                point = point.tag(key, str(value))
        for key, value in fields.items():
            if value is not None:
                point = point.field(key, value)
        point = point.time(timestamp, WritePrecision.S)

        try:
            self._write_api.write(bucket=self._bucket, org=self._org, record=point)
        except InfluxDBError as exc:
            raise WriteError(f"InfluxDB write failed for [{measurement}]: {exc}") from exc

    def write_batch(self, points: list[dict]) -> None:
        """
        Write multiple points in one API call.
        Each dict must have keys: measurement, tags, fields, timestamp (optional).
        """
        influx_points: list[Point] = []
        for p in points:
            ts = p.get("timestamp") or datetime.now(timezone.utc)
            point = Point(p["measurement"])
            for k, v in p.get("tags", {}).items():
                if v is not None:
                    point = point.tag(k, str(v))
            for k, v in p.get("fields", {}).items():
                if v is not None:
                    point = point.field(k, v)
            point = point.time(ts, WritePrecision.S)
            influx_points.append(point)

        try:
            self._write_api.write(
                bucket=self._bucket, org=self._org, record=influx_points
            )
        except InfluxDBError as exc:
            raise WriteError(f"InfluxDB batch write failed: {exc}") from exc

    def close(self) -> None:
        self._write_api.close()
        self._client.close()
