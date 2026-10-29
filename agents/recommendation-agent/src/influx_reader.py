from influxdb_client import InfluxDBClient


class InfluxReader:
    def __init__(self, url: str, token: str, org: str, bucket: str) -> None:
        self._client = InfluxDBClient(url=url, token=token, org=org)
        self._query_api = self._client.query_api()
        self._org = org
        self._bucket = bucket

    def get_latest_metrics(self) -> dict[str, list[dict]]:
        measurements = [
            "server_health",
            "disk_health",
            "service_health",
            "esxi_health",
            "vm_health",
            "siemens_plc_health",
            "scada_tag_health",
        ]
        return {measurement: self._latest(measurement) for measurement in measurements}

    def close(self) -> None:
        self._client.close()

    def _latest(self, measurement: str) -> list[dict]:
        query = f'''
from(bucket: "{self._bucket}")
  |> range(start: -15m)
  |> filter(fn: (r) => r._measurement == "{measurement}")
  |> last()
  |> pivot(rowKey: ["source_id"], columnKey: ["_field"], valueColumn: "_value")
'''
        tables = self._query_api.query(query, org=self._org)
        results = []
        for table in tables:
            for record in table.records:
                results.append(record.values)
        return results
