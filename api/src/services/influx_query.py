"""
Flux query builder for InfluxDB.
Abstracts all Flux query construction so routers stay clean.
"""
from __future__ import annotations

from influxdb_client import InfluxDBClient


class InfluxQueryService:
    def __init__(self, client: InfluxDBClient, bucket: str, org: str) -> None:
        self._query_api = client.query_api()
        self._bucket = bucket
        self._org = org

    # ── Servers ──────────────────────────────────────────────────────────────

    def get_servers_latest(self, source_id: str | None = None) -> list[dict]:
        """Latest server_health point per server."""
        filter_clause = (
            f'|> filter(fn: (r) => r["source_id"] == "{source_id}")'
            if source_id else ""
        )
        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -10m)
          |> filter(fn: (r) => r["_measurement"] == "server_health")
          {filter_clause}
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "hostname", "collection_method"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    def get_disks_latest(self, source_id: str | None = None) -> list[dict]:
        """Latest disk_health point per (server, drive)."""
        filter_clause = (
            f'|> filter(fn: (r) => r["source_id"] == "{source_id}")'
            if source_id else ""
        )
        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -10m)
          |> filter(fn: (r) => r["_measurement"] == "disk_health")
          {filter_clause}
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "drive_letter"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    def get_services_latest(self, source_id: str | None = None) -> list[dict]:
        """Latest service_health point per (server, service)."""
        filter_clause = (
            f'|> filter(fn: (r) => r["source_id"] == "{source_id}")'
            if source_id else ""
        )
        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -10m)
          |> filter(fn: (r) => r["_measurement"] == "service_health")
          {filter_clause}
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "service_name"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    def get_server_history(self, source_id: str, range_minutes: int = 1440) -> list[dict]:
        """Time-series history for a single server."""
        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -{range_minutes}m)
          |> filter(fn: (r) => r["_measurement"] == "server_health")
          |> filter(fn: (r) => r["source_id"] == "{source_id}")
          |> filter(fn: (r) => r["_field"] == "cpu_usage_percent"
                            or r["_field"] == "ram_usage_percent"
                            or r["_field"] == "reachable")
        """
        return self._execute(flux)

    # ── VMware ───────────────────────────────────────────────────────────────

    def get_esxi_hosts_latest(self) -> list[dict]:
        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r["_measurement"] == "esxi_health")
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "hostname", "version"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    def get_vms_latest(
        self,
        esxi_host: str | None = None,
        power_state: str | None = None,
    ) -> list[dict]:
        filters = []
        if esxi_host:
            filters.append(f'r["esxi_host"] == "{esxi_host}"')
        if power_state:
            filters.append(f'r["power_state"] == "{power_state}"')

        extra_filter = ""
        if filters:
            combined = " and ".join(filters)
            extra_filter = f"|> filter(fn: (r) => {combined})"

        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r["_measurement"] == "vm_health")
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "vm_name", "esxi_host", "guest_os"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          {extra_filter}
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    # ── Siemens PLCs ─────────────────────────────────────────────────────────

    def get_siemens_plcs_latest(
        self,
        source_id: str | None = None,
        plant: str | None = None,
    ) -> list[dict]:
        filters = []
        if source_id:
            filters.append(f'r["source_id"] == "{source_id}"')
        if plant:
            filters.append(f'r["plant"] == "{plant}"')

        extra_filter = ""
        if filters:
            combined = " and ".join(filters)
            extra_filter = f"|> filter(fn: (r) => {combined})"

        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r["_measurement"] == "siemens_plc_health")
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "plc_name", "plant", "model", "firmware", "collection_method"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          {extra_filter}
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _execute(self, flux: str) -> list[dict]:
        tables = self._query_api.query(flux, org=self._org)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results
