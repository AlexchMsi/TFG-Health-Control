from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    influxdb_url: str = "http://influxdb:8086"
    influxdb_org: str = "gea"
    influxdb_bucket: str = "health_status"
    influxdb_admin_token: str = "change-me-in-production"
    log_level: str = "INFO"
    ollama_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.1:8b"
    analysis_interval_minutes: int = 15
    recommendations_path: str = "/app/data/recommendations.json"
