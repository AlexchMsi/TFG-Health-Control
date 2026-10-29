import json


def build_prompt(metrics: dict[str, list[dict]]) -> str:
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
