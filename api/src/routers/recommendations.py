import json
from pathlib import Path

import httpx
from fastapi import APIRouter, Request

from ..services.influx_query import InfluxQueryService

router = APIRouter()

RECOMMENDATIONS_PATH = Path("/app/data/recommendations.json")

_MEASUREMENTS = [
    "server_health",
    "disk_health",
    "service_health",
    "esxi_health",
    "vm_health",
    "siemens_plc_health",
    "scada_tag_health",
]


def _svc(request: Request) -> InfluxQueryService:
    return InfluxQueryService(
        request.app.state.influx,
        request.app.state.bucket,
        request.app.state.org,
    )


def _build_prompt(metrics: dict[str, list[dict]]) -> str:
    payload = json.dumps(metrics, ensure_ascii=False, default=str)
    return f"""
Eres un asistente de operación industrial OT. Analiza métricas recientes de salud de servidores, discos, servicios, ESXi, VMs, PLC Siemens y tags SCADA.

Reglas:
- Prioriza equipos no alcanzables, servicios parados, discos con poco espacio, CPU/RAM alta, PLCs en fallo y tags SCADA con mala calidad o sin actualización.
- Incluye scada_tag_health en el análisis.
- No inventes datos que no estén en las métricas.
- Responde en español.
- Devuelve JSON estricto sin markdown, sin texto adicional.

Formato JSON estricto:
{{
  "summary": "resumen breve",
  "risk_level": "low|medium|high|critical",
  "recommendations": [
    {{"priority": "low|medium|high|critical", "source_id": "id", "finding": "hallazgo", "action": "acción recomendada"}}
  ]
}}

Métricas:
{payload}
""".strip()


def _metrics(request: Request) -> dict[str, list[dict]]:
    svc = _svc(request)
    return {measurement: svc.get_latest_by_measurement(measurement) for measurement in _MEASUREMENTS}


def _parse(raw: str) -> dict:
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "summary": "No se pudo interpretar la respuesta del modelo.",
            "risk_level": "medium",
            "recommendations": [
                {"priority": "medium", "source_id": "ai", "finding": raw, "action": "Revisar la salida del modelo."}
            ],
        }


@router.get("/latest")
async def latest():
    if not RECOMMENDATIONS_PATH.exists():
        return []
    return json.loads(RECOMMENDATIONS_PATH.read_text(encoding="utf-8"))


@router.post("/analyze")
async def analyze(request: Request):
    settings = request.app.state.settings
    prompt = _build_prompt(_metrics(request))
    async with httpx.AsyncClient(timeout=300) as client:
        response = await client.post(
            f"{settings.ollama_url.rstrip('/')}/api/generate",
            json={"model": settings.ollama_model, "prompt": prompt, "stream": False},
        )
    response.raise_for_status()
    return _parse(response.json()["response"])
