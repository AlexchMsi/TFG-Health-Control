# Planning noviembre–diciembre 2026 (2 días/semana)

Punto de partida (30-oct): plataforma funcional validada end-to-end en local
(89 tests, UI completa, correcciones de fiabilidad aplicadas). Pendiente:
validación con equipos reales en GEA, seguridad mínima de la API, decidir si
entran alertas, y la memoria (lo más pesado).

**Principio rector**: congelar funcionalidades a final de noviembre.
Diciembre es para escribir. Con ~16 días reales de trabajo, la memoria
necesita al menos 8.

## Decisiones a confirmar con los tutores (semana 1, por email si hace falta)

1. Convocatoria y fecha límite exacta de entrega/defensa.
2. ¿El alcance exige agente Rockwell y/o monitorización de red? (propuesta: trabajo futuro).
3. ¿Las alertas operativas (email/Teams) entran en el alcance o son evolución?
4. Qué documento de memoria es el "principal" (hay 6 versiones .docx — consolidar en una).

## Calendario

### Semana 1 (3–9 nov) — Validación en umbrella  🎯 Hito M1
- **Día 1**: despliegue en umbrella + smoke test con simuladores + primera estación de ingeniería por SNMP (seguir `docs/Tutorial_prueba_umbrella.md`).
- **Día 2**: WinRM con servicios críticos + PLC/SCADA real si hay permiso OT. **Capturar evidencias** (pantallazos con hora, logs, valores).
- Si el acceso OT se retrasa: documentarlo, pedir fecha, y seguir el plan — nada de diciembre depende de esto.

### Semana 2 (10–16 nov) — Flecos de la prueba real + seguridad mínima
- **Día 1**: corregir lo que haya fallado en umbrella (siempre sale algo: timeouts, firewall, parseos).
- **Día 2**: seguridad mínima exigible en una red de cliente: API key en los endpoints de escritura (/config, /recommendations/analyze), no devolver contraseñas en los GET de targets, fijar dependencias sueltas. Con tests.

### Semana 3 (17–23 nov) — Alertas (si entran) o adelantar memoria
- **Si el tutor confirma alertas**: reglas de Grafana Alerting sobre `reachable=0`, disco >90 %, servicio parado → email/Teams. Es demo potente y capítulo de memoria.
- **Si no entran**: adelantar semana 4.
- **Fin de semana 3 = feature freeze.** 🎯 Hito M2: plataforma congelada, solo bugfixes.

### Semana 4 (24–30 nov) — Memoria I: estructura y consolidación
- **Día 1**: consolidar las 6 versiones .docx en UNA sobre la plantilla oficial (Anexo III). Índice definitivo cerrado.
- **Día 2**: capítulos de contexto: problema, objetivos, estado del arte (ya hay material en docs/ y en versiones previas — es reorganizar, no escribir de cero).

### Semana 5 (1–7 dic) — Memoria II: núcleo técnico
- **Día 1**: arquitectura y decisiones de diseño (diagramas de flujo de datos, tabla de protocolos, esquema de measurements).
- **Día 2**: implementación por componente (shared, agentes, API, UI, IA). Ojo: puente 6–8 dic, planificar los 2 días antes del puente.

### Semana 6 (8–14 dic) — Memoria III: pruebas y resultados  🎯 Hito M3
- **Día 1**: metodología de pruebas (89 tests unitarios + validación end-to-end) y resultados con las evidencias de umbrella. Sin inventar cifras: lo validado con simulador se presenta como tal.
- **Día 2**: limitaciones (cpu_state vía gateway, WinRM, sin autenticación completa...), conclusiones contra objetivos, implicaciones éticas, trabajo futuro (Rockwell, red, reporting).
- **Fin de semana 6 = borrador completo.**

### Semana 7 (15–21 dic) — Memoria IV: acabado y entrega a tutores  🎯 Hito M4
- **Día 1**: figuras numeradas, tablas, índices, referencias (formato de la plantilla), anexos (manual de despliegue = docs/Despliegue_GEA.md adaptado).
- **Día 2**: lectura completa, coherencia, portada/datos académicos confirmados → **enviar a Roque y Jaime antes de Navidad**.

### Semana 8 (22–28 dic) — Buffer
- Correcciones de tutores si llegan, pulir la demo (guion de demostración con la UI + Grafana + una caída provocada), descanso ganado.

## Riesgos y plan B

| Riesgo | Mitigación |
|---|---|
| Sin acceso a PLC real en nov | Resultados con simulador OPC UA + PLCSIM, documentado como limitación; pedir ventana OT para enero |
| Umbrella sin recursos para Ollama | Stack sin IA en umbrella; demo de IA en tu PC |
| Scope creep (ganas de añadir Rockwell…) | Feature freeze 23-nov; todo lo nuevo → "trabajo futuro" |
| Las 6 versiones de memoria se contradicen | Día dedicado a consolidar (S4-D1) antes de escribir nada nuevo |
| Puente + Navidad se comen diciembre | El borrador completo es el 14-dic, no el 21; S8 es buffer, no plan |

## Resumen de hitos

- **M1 (9 nov)**: sistema validado en umbrella (con reales o con sims + fecha OT).
- **M2 (23 nov)**: feature freeze — plataforma cerrada.
- **M3 (14 dic)**: borrador completo de la memoria.
- **M4 (21 dic)**: memoria enviada a tutores.
