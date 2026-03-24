from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # InfluxDB
    influxdb_url: str = "http://influxdb:8086"
    influxdb_org: str = "gea"
    influxdb_bucket: str = "health_status"
    influxdb_admin_token: str = "change-me-in-production"

    # Agent
    poll_interval_seconds: int = 60
    log_level: str = "INFO"

    # VMware
    vmware_host: str = ""
    vmware_user: str = ""
    vmware_password: str = ""
    vmware_ignore_ssl: bool = False

    # SNMP
    snmp_community: str = "public"
    snmp_version: str = "2c"

    # WinRM
    winrm_user: str = ""
    winrm_password: str = ""
    winrm_transport: str = "ntlm"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
