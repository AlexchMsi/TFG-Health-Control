"""
Flux query builder for InfluxDB.
Abstracts all Flux query construction so routers stay clean.
"""
from __future__ import annotations

from influxdb_client import InfluxDBClient


def _esc(value: str) -> str:
    """Escape a value for interpolation inside a double-quoted Flux string literal."""
    return value.replace("\\", "\\\\").replace('"', '\\"')


class InfluxQueryService:
    def __init__(self, client: InfluxDBClient, bucket: str, org: str) -> None:
        self._query_api = client.query_api()
        self._bucket = bucket
        self._org = org

    # ── Servers ──────────────────────────────────────────────────────────────

    def get_servers_latest(self, source_id: str | None = None) -> list[dict]:
        """Latest server_health point per server."""
        filter_clause = (
            f'|> filter(fn: (r) => r["source_id"] == "{_esc(source_id)}")'
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
            f'|> filter(fn: (r) => r["source_id"] == "{_esc(source_id)}")'
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
            f'|> filter(fn: (r) => r["source_id"] == "{_esc(source_id)}")'
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
          |> range(start: -{int(range_minutes)}m)
          |> filter(fn: (r) => r["_measurement"] == "server_health")
          |> filter(fn: (r) => r["source_id"] == "{_esc(source_id)}")
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
          |> filter(fn: (r) => exists r["version"])
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
            filters.append(f'r["esxi_host"] == "{_esc(esxi_host)}"')
        if power_state:
            filters.append(f'r["power_state"] == "{_esc(power_state)}"')

        extra_filter = ""
        if filters:
            combined = " and ".join(filters)
            extra_filter = f"|> filter(fn: (r) => {combined})"

        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r["_measurement"] == "vm_health")
          |> filter(fn: (r) => exists r["guest_os"])
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
            filters.append(f'r["source_id"] == "{_esc(source_id)}"')
        if plant:
            filters.append(f'r["plant"] == "{_esc(plant)}"')

        extra_filter = ""
        if filters:
            combined = " and ".join(filters)
            extra_filter = f"|> filter(fn: (r) => {combined})"

        flux = f"""
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r["_measurement"] == "siemens_plc_health")
          |> filter(fn: (r) => exists r["model"] and exists r["firmware"])
          |> last()
          |> pivot(rowKey: ["_time", "source_id", "plc_name", "plant", "model", "firmware", "collection_method"],
                   columnKey: ["_field"],
                   valueColumn: "_value")
          {extra_filter}
          |> drop(columns: ["_start", "_stop", "_measurement"])
        """
        return self._execute(flux)

    # ── SCADA ────────────────────────────────────────────────────────────────

    def get_scada_latest(
        self,
        source_id: str | None = None,
        scada_type: str | None = None,
        tag_name: str | None = None,
    ) -> list[dict]:
        filters = []
        if source_id:
            filters.append(f'r["source_id"] == "{_esc(source_id)}"')
        if scada_type:
            filters.append(f'r["scada_type"] == "{_esc(scada_type)}"')
        if tag_name:
            filters.append(f'r["tag_name"] == "{_esc(tag_name)}"')

        extra_filter = ""
        if filters:
            combined = " and ".join(filters)
            extra_filter = f"|> filter(fn: (r) => {combined})"

        flux = f'''
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r._measurement == "scada_tag_health")
          {extra_filter}
          |> last()
          |> pivot(rowKey: ["source_id", "scada_type", "tag_name"], columnKey: ["_field"], valueColumn: "_value")
        '''
        return self._execute(flux)

    def get_scada_history(
        self,
        source_id: str,
        tag_name: str | None = None,
        range_minutes: int = 1440,
    ) -> list[dict]:
        tag_filter = f'|> filter(fn: (r) => r["tag_name"] == "{_esc(tag_name)}")' if tag_name else ""
        flux = f'''
        from(bucket: "{self._bucket}")
          |> range(start: -{int(range_minutes)}m)
          |> filter(fn: (r) => r._measurement == "scada_tag_health")
          |> filter(fn: (r) => r["source_id"] == "{_esc(source_id)}")
          {tag_filter}
          |> filter(fn: (r) => r._field == "value_float" or r._field == "value_string" or r._field == "value_bool" or r._field == "quality" or r._field == "reachable")
        '''
        return self._execute(flux)

    # ── Cross-measurement (recommendations) ──────────────────────────────────

    def get_latest_by_measurement(self, measurement: str) -> list[dict]:
        """Latest points of one measurement, pivoted by source_id (recommendation input)."""
        flux = f'''
        from(bucket: "{self._bucket}")
          |> range(start: -15m)
          |> filter(fn: (r) => r._measurement == "{_esc(measurement)}")
          |> last()
          |> pivot(rowKey: ["source_id"], columnKey: ["_field"], valueColumn: "_value")
        '''
        return self._execute(flux)

    # ── Internal ─────────────────────────────────────────────────────────────

    def _execute(self, flux: str) -> list[dict]:
        tables = self._query_api.query(flux, org=self._org)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results
