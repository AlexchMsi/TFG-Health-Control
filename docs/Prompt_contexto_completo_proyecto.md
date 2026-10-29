# Prompt de contexto completo — Control System Health Status

Quiero que continúes ayudándome con mi TFG/PFG “Control System Health Status”.

Este es el contexto del proyecto. Úsalo como punto de partida, pero contrástalo con el repositorio antes de proponer cambios: existen documentos desactualizados, diferencias entre versiones de la memoria y trabajo local todavía sin incorporar a Git.

# 1. Tu papel y cómo debes trabajar conmigo

Actúa como asistente técnico para desarrollar, validar y documentar el proyecto.

Necesito ayuda con:
- Arquitectura y desarrollo de software.
- Integración con infraestructura industrial.
- Monitorización IT/OT.
- Pruebas, diagnóstico y despliegue.
- Documentación técnica y memoria académica.

Comunícate conmigo en español, de forma clara y directa. Explica las decisiones importantes y sus motivos.

Antes de modificar código:
1. Lee las instrucciones aplicables de AGENTS.md y el contexto de prompt.md.
2. Revisa el estado real del repositorio y los cambios locales.
3. Comprueba cómo está implementada la parte afectada.
4. Pregunta por las decisiones ambiguas; no inventes requisitos.
5. Presenta un plan proporcionado al trabajo y sigue el flujo de aprobación indicado por las instrucciones del proyecto.

Utiliza subagentes especializados cuando estén disponibles y las instrucciones del repositorio lo indiquen. Paraleliza tareas independientes.

Después de modificar:
- Ejecuta las comprobaciones apropiadas para esta aplicación.
- Explica qué se ha probado, con qué resultado y qué sigue sin verificarse.
- Actualiza la documentación pertinente cuando cambien arquitectura o comportamiento.

No confundas:
- Planificado.
- Implementado.
- Probado unitariamente.
- Integrado.
- Validado con equipos reales.
- Validado en producción.

No afirmes que algo funciona por el mero hecho de que exista su código.

# 2. Qué es el proyecto

“Control System Health Status” es una plataforma modular para monitorizar la salud de infraestructura industrial IT/OT.

El proyecto se desarrolla en el contexto de una colaboración con GEA Process Engineering.

En estos entornos conviven:
- Servidores Windows.
- Hipervisores VMware ESXi.
- Máquinas virtuales.
- PLCs.
- Sistemas SCADA.
- Redes industriales.

El problema es que su supervisión suele estar fragmentada entre herramientas y fabricantes. Esto complica obtener una visión conjunta, diagnosticar incidencias y detectar degradaciones.

La propuesta consiste en recoger métricas mediante agentes especializados, almacenarlas de forma homogénea y ofrecer consulta, visualización y apoyo al diagnóstico desde una plataforma común.

La adquisición debe ser de solo lectura respecto a los equipos y procesos supervisados.

Los beneficios esperados son mejorar la visibilidad, facilitar el mantenimiento y reducir el tiempo de diagnóstico. Son objetivos: no hay que presentarlos como mejoras cuantificadas sin mediciones que los demuestren.

# 3. Objetivo general

Diseñar e implementar una plataforma modular, extensible y desplegable mediante contenedores para centralizar la monitorización de infraestructura industrial heterogénea.

Debe permitir:
- Adquirir métricas de diferentes tecnologías.
- Mantener histórico.
- Gestionar dinámicamente los equipos monitorizados.
- Consultar información mediante una API.
- Visualizarla en dashboards.
- Incorporar apoyo al diagnóstico mediante recomendaciones.

# 4. Objetivos específicos

1. Analizar las necesidades y restricciones de un entorno industrial IT/OT.
2. Seleccionar protocolos y métricas adecuados para cada tipo de activo.
3. Separar adquisición, almacenamiento, configuración, consulta y visualización.
4. Monitorizar Windows mediante SNMP y WinRM.
5. Monitorizar ESXi y máquinas virtuales mediante la API de VMware.
6. Monitorizar PLCs Siemens mediante OPC UA y Snap7/S7Comm.
7. Recoger tags de sistemas SCADA mediante OPC UA.
8. Almacenar métricas temporales en InfluxDB.
9. Gestionar targets mediante FastAPI y SQLite.
10. Permitir altas, bajas y activación/desactivación sin reiniciar los agentes.
11. Proporcionar dashboards Grafana provisionados.
12. Generar recomendaciones en español mediante un modelo local servido por Ollama.
13. Desarrollar pruebas y validar el recorrido completo de los datos.
14. Documentar decisiones, resultados, limitaciones y trabajo futuro en la memoria del TFG.

La integración con la plataforma corporativa Codex de GEA aparece como objetivo documental, pero no debe darse por completada sin evidencias.

No confundas Codex de GEA con herramientas de desarrollo de OpenAI.

# 5. Alcance y estado general

Hay implementación para:
- Biblioteca compartida.
- API de configuración y consulta.
- Interfaz web de administración de targets.
- Agente de servidores Windows y VMware.
- Agente Siemens.
- Agente SCADA.
- Agente de recomendaciones con Ollama.
- Dashboards Grafana.
- Despliegue mediante Docker Compose.
- Pruebas principalmente unitarias.

Las ampliaciones SCADA y recomendaciones forman parte del trabajo local más reciente. No están completamente reflejadas en la documentación antigua ni en el último estado confirmado en Git.

Todavía no están implementados como agentes funcionales:
- Rockwell.
- Monitorización específica de red industrial.

También figuran como evolución:
- Alertas operativas y notificaciones.
- Reporting.
- Ampliaciones de integración y despliegue.

El alcance académico definitivo debe confirmarse: los documentos no coinciden en qué ampliaciones son obligatorias para entregar el TFG y cuáles son trabajo futuro.

Evita depender de la numeración de fases, porque cambia entre documentos. Identifica los hitos por nombre.

# 6. Stack tecnológico real

Backend y agentes:
- Python 3.12.
- FastAPI.
- Uvicorn.
- Pydantic y pydantic-settings.
- SQLModel con SQLite.
- APScheduler.

Datos y visualización:
- InfluxDB 2.7.
- Consultas Flux.
- Grafana OSS 10.4.

Protocolos y librerías:
- SNMPv2c con pysnmp-lextudio.
- WinRM y PowerShell con pywinrm.
- VMware vSphere API con pyVmomi.
- OPC UA con asyncua.
- S7Comm con python-snap7.
- HTTP mediante Requests o HTTPX según el componente.

IA:
- Ollama.
- Modelo predeterminado: llama3.1:8b.
- El modelo efectivo depende de la configuración de ejecución.

Frontend:
- HTML.
- JavaScript sin framework.
- Tailwind cargado desde CDN.
- No hay aplicación React o Next.js ni compilación frontend propia.

Infraestructura:
- Docker.
- Docker Compose.
- Volúmenes persistentes.
- Red interna entre servicios.

Pruebas:
- Pytest.

Dependencias especialmente sensibles:
- pysnmp-lextudio==5.0.34.
- pyasn1==0.5.1.

No actualices estas versiones SNMP sin investigar las incompatibilidades documentadas y probar la solución.

Comprueba los requirements actuales antes de citar otras versiones. Algunas dependencias no están completamente fijadas y Ollama usa actualmente una etiqueta de imagen mutable.

# 7. Estructura del repositorio

Directorio de trabajo observado:
C:\Universidad\ftg

Estructura principal:

api/
  src/
    main.py
    database.py
    models/
    routers/
    services/influx_query.py
    static/index.html

shared/
  config/
  models/
  influx/writer.py
  utils/

agents/
  server-agent/
  siemens-agent/
  scada-agent/
  recommendation-agent/
  rockwell-agent/
  network-agent/

infra/
  grafana/
    dashboards/
    provisioning/

tests/
scripts/
docs/
data/

Archivos relevantes:
- docker-compose.yml.
- README.md.
- AGENTS.md.
- CLAUDE.md.
- prompt.md.
- pytest.ini.
- requirements-dev.txt.
- .env.example.

No expongas valores de .env ni credenciales de targets. Los datos persistidos pueden contener información sensible del entorno.

# 8. Arquitectura y flujo de datos

Flujo de configuración:

Usuario o cliente HTTP
→ Interfaz web / API FastAPI
→ SQLite
→ ConfigPoller de cada agente de adquisición
→ Alta o retirada de trabajos APScheduler.

Flujo de adquisición:

Equipo supervisado
→ Collector
→ Modelo de métrica tipado
→ Scheduler del agente
→ InfluxWriter
→ InfluxDB.

Flujo de consulta:

InfluxDB
→ API de métricas y Grafana.

Flujo de recomendaciones:

InfluxDB
→ Agente de recomendaciones
→ Ollama
→ Análisis estructurado
→ Archivo JSON persistido
→ API de recomendaciones.

Importante:
- Los agentes de servidores, Siemens y SCADA escriben directamente en InfluxDB.
- La API no es el punto de ingestión de sus métricas.
- El agente de recomendaciones lee métricas; no sigue el mismo flujo de escritura que los agentes de adquisición.
- SQLite guarda configuración.
- InfluxDB guarda series temporales.
- El JSON de recomendaciones guarda análisis recientes.
- La adquisición es periódica por polling, no streaming continuo.

# 9. Gestión dinámica de targets

Un target contiene, entre otros:
- id.
- plant.
- agent_type.
- display_name.
- enabled.
- config.
- Fechas de creación y actualización.

La configuración específica del protocolo se guarda dentro de config.

Los agentes de adquisición consultan la API cada 30 segundos para sincronizar sus targets.

Se implementan:
- Altas.
- Bajas.
- Activación y desactivación.

Limitación detectada en la lectura del código:
El poller compara los IDs habilitados, pero no aplica correctamente cambios de configuración de un target que conserva el mismo ID.

Por tanto, no afirmes que cambiar host, credenciales, protocolo o intervalo mediante la API reconfigura automáticamente un trabajo existente.

Los 30 segundos son el intervalo de sincronización de configuración; no garantizan una latencia extremo a extremo de 30 segundos hasta Grafana.

# 10. Componentes y funcionalidades

## 10.1. server-agent: Windows

Métodos:
- SNMP.
- WinRM.

SNMP recoge:
- Disponibilidad.
- Uptime.
- CPU.
- RAM.
- Discos.
- Información del sistema.

WinRM ejecuta PowerShell remoto para obtener recursos y contempla servicios críticos e información de sincronización horaria.

Limitaciones identificadas:
- La interfaz no expone toda la configuración necesaria para WinRM.
- La lista de servicios críticos no está correctamente conectada con la ejecución del script remoto.
- Algunas lecturas incompletas pueden convertirse en ceros.
- La interpretación de ciertos resultados depende del formato o idioma.

## 10.2. server-agent: VMware

VMware es un método del agente de servidores, no un agente independiente.

Usa pyVmomi para consultar vCenter o ESXi.

Métricas previstas e implementadas en distinto grado:
- CPU y RAM de hosts.
- Uptime.
- Estado de conexión.
- Modo mantenimiento.
- Número de VMs.
- Estado de encendido de VMs.
- CPU y RAM de VMs.
- VMware Tools.
- Snapshots y antigüedad del más antiguo.

Limitaciones:
- Un fallo completo de conexión no genera actualmente una métrica explícita de inaccesibilidad.
- Hay campos modelados que no se recogen o persisten efectivamente.
- Debe revisarse la unicidad de identificadores al monitorizar varios entornos VMware.

## 10.3. siemens-agent

Métodos:
- opcua.
- snap7.
- auto: OPC UA primero y Snap7 como alternativa.

Busca obtener:
- Estado del controlador.
- Información de CPU.
- Memoria.
- Diagnóstico.
- Disponibilidad.

Hay que distinguir los campos definidos en los modelos de los valores realmente adquiridos.

Limitaciones importantes:
- El estado de un servidor OPC UA no demuestra necesariamente el estado RUN/STOP de la CPU física.
- Actualmente existe una confusión entre CPU en RUN y equipo alcanzable.
- Un PLC accesible en STOP no debería considerarse automáticamente inaccesible.
- Algunos campos de diagnóstico siguen sin adquisición efectiva.
- Snap7, sus estructuras y los timeouts requieren validación con hardware real.

## 10.4. scada-agent

Es un agente independiente para leer tags de proceso mediante OPC UA.

Admite:
- Lista explícita de tags.
- Valores numéricos.
- Booleanos.
- Texto.
- Información de lectura correcta o fallida.
- Usuario y contraseña.
- Clasificación heurística del fabricante del servidor.

Puede reconocer indicios de plataformas como:
- Ignition.
- WinCC.
- FactoryTalk.
- AVEVA.

Esto no significa que existan cuatro conectores nativos: se usa un recolector OPC UA genérico con detección heurística.

Diferencia fundamental:
- Siemens supervisa la salud del controlador.
- SCADA recoge variables expuestas por un servidor OPC UA.

Limitaciones:
- GOOD/BAD se deriva principalmente del éxito o fallo de lectura.
- No se conserva explícitamente toda la calidad original OPC UA ni el timestamp de origen.
- No hay detección demostrada de tags congelados.
- No hay descubrimiento automático completo de tags.
- La configuración de certificados y políticas de seguridad requiere desarrollo o revisión.

## 10.5. recommendation-agent y Ollama

Esta ampliación usa un modelo preentrenado local para interpretar métricas recientes y proponer recomendaciones en español.

Funcionamiento:
1. Espera disponibilidad de Ollama.
2. Solicita la disponibilidad/descarga del modelo configurado.
3. Lee los últimos valores de métricas dentro de una ventana de 15 minutos.
4. Construye un prompt de operación industrial.
5. Solicita una respuesta al modelo.
6. Interpreta el resultado como JSON.
7. Conserva hasta diez análisis recientes en un archivo persistido.

Ejecuta un primer análisis y después uno cada 15 minutos por defecto.

La respuesta esperada incluye:
- summary.
- risk_level: low, medium, high o critical.
- recommendations.
- Para cada recomendación: priority, source_id, finding y action.

Debe priorizar problemas como:
- Equipos no alcanzables.
- Servicios detenidos.
- Discos con poco espacio.
- Uso elevado de CPU/RAM.
- Problemas de PLC.
- Errores de tags SCADA.

Límites importantes:
- No se está entrenando un modelo propio.
- No hay fine-tuning, RAG ni dataset de aprendizaje documentado.
- No es un sistema predictivo validado.
- Trabaja fundamentalmente con últimos valores recientes, no con un modelo temporal entrenado.
- Las recomendaciones no ejecutan reparaciones ni escriben sobre PLCs.
- No hay evaluación cuantitativa de la calidad del modelo.

Aspectos pendientes:
- Validación del esquema JSON.
- Recuperación del histórico tras reinicios.
- Escritura atómica del archivo.
- Coherencia entre análisis manual y periódico.
- Manejo de errores y tiempos de respuesta.
- Evitar llamadas bloqueantes prolongadas dentro de rutas async.
- Evitar duplicación de prompts y consultas.
- Validar recursos, latencia y funcionamiento sin conexión a Internet.

# 11. Modelo de métricas

Measurements principales:
- server_health.
- disk_health.
- service_health.
- esxi_health.
- vm_health.
- siemens_plc_health.
- scada_tag_health.

Los modelos de shared/models son modelos de datos/dataclasses, no modelos de machine learning.

Reglas arquitectónicas declaradas:
- Mantener modelos tipados entre adquisición y escritura.
- Usar InfluxWriter como punto común de escritura a InfluxDB.
- Utilizar WritePrecision.S.
- Persistir reachable como entero cuando corresponda.
- Separar identificadores estables y valores medidos.
- Evitar que el fallo de un target detenga la supervisión de los demás.
- Representar los errores de adquisición de forma controlada.

Estas reglas son contratos que hay que preservar y comprobar: existen incumplimientos o comportamientos parciales en componentes actuales.

Debe revisarse:
- La semántica de disponibilidad.
- La coherencia temporal de los campos.
- El tratamiento de valores ausentes.
- La posibilidad de mostrar valores antiguos como actuales.
- La cardinalidad.
- La identificación consistente de planta y activo.

# 12. API e interfaz web

API FastAPI con documentación OpenAPI.

Rutas principales:
- /health/
- /config/targets
- /config/targets/{target_id}
- /metrics/servers/
- /metrics/vmware/hosts
- /metrics/vmware/vms
- /metrics/plcs/siemens
- /metrics/scada/
- /recommendations/latest
- /recommendations/analyze
- /ui
- /docs

Consulta los routers para conocer los métodos y subrutas exactos.

La interfaz web permite:
- Listar targets.
- Añadirlos.
- Activarlos o pausarlos.
- Eliminarlos.
- Adaptar campos según el tipo de equipo y protocolo.

No debe describirse como una interfaz completa de operación:
- No tiene edición general de targets.
- No presenta todas las métricas.
- No muestra actualmente las recomendaciones.
- No sustituye a Grafana.

Las consultas Flux de la API deberían estar encapsuladas en su capa de servicios. Actualmente el router de recomendaciones contiene consultas propias: es una desviación respecto a esa organización.

# 13. Grafana

Existen dashboards para:
- Servidores.
- PLC Siemens.
- Tags SCADA.

Se provisionan desde archivos del repositorio.

Hay que validar:
- Referencias al datasource.
- Resolución del bucket.
- Variables de dashboards.
- Semántica de las consultas.
- Comportamiento ante pérdida de comunicación.
- Coherencia entre el estado mostrado y la última muestra real.

Los umbrales visuales de un panel no equivalen a alertas operativas.

No hay evidencia de reglas completas de alertas, destinatarios y políticas de notificación ya configuradas.

# 14. Despliegue

Docker Compose declara:
- InfluxDB.
- Grafana.
- API.
- Agente de servidores.
- Agente Siemens.
- Agente SCADA.
- Ollama.
- Agente de recomendaciones.
- Objetivo SNMP de pruebas.

Puertos habituales:
- API: 8000.
- Grafana: 3000.
- InfluxDB: 8086.
- Ollama: 11434.
- Objetivo SNMP de pruebas: 1161/UDP.

Accesos locales habituales:
- http://localhost:8000/ui
- http://localhost:8000/docs
- http://localhost:3000

Existe scripts/setup_windows.ps1 para instalación nativa, pero no es equivalente al Compose actual ni debe darse por validado.

Antes de utilizarlo hay que revisar:
- Rutas.
- Instalación de dependencias.
- SQLite.
- Registro de servicios.
- Generación de configuración.
- Componentes que no instala.
- Tratamiento de credenciales.

Hay scripts de exploración OPC UA, Snap7 y conectividad. Revisa su implementación: algunos usan configuración antigua o comprueban solo parte de la conectividad.

En Windows y Docker pueden aparecer problemas de rutas de red, adaptadores virtuales, firewall, VMware y acceso a equipos OT. Diagnostica desde el entorno real de ejecución del agente, no únicamente desde el host.

# 15. Estado de las pruebas y validación

Existe una suite Pytest para:
- Modelos.
- Escritura de métricas.
- Poller y schedulers.
- Collectors.
- API.
- Consultas.
- UI básica.
- Recomendaciones.

Son principalmente pruebas unitarias con dobles o mocks.

No demuestran por sí solas:
- Comunicación real con PLCs.
- Compatibilidad completa de Snap7.
- Ejecución real de Flux.
- Aprovisionamiento correcto de Grafana.
- Calidad de recomendaciones.
- Funcionamiento integral en producción.

No reutilices cifras antiguas de tests como resultado actual. La documentación contiene cifras diferentes y algunas pruebas pueden omitirse si faltan dependencias.

Para cambios futuros:
- Ejecuta pytest cuando corresponda.
- Comprueba la configuración y construcción Docker según el cambio.
- Usa herramientas de lint o tipado si realmente están disponibles.
- No inventes npm, Next.js o next build para este repositorio.

La validación integral con activos reales sigue pendiente según la documentación de estado más explícita.

# 16. Prioridades pendientes

La prioridad no debería ser ampliar funcionalidades indefinidamente, sino consolidar y validar lo construido.

Bloques de trabajo:
1. Corregir la actualización dinámica de targets existentes.
2. Revisar configuración y adquisición WinRM.
3. Corregir la semántica de disponibilidad de VMware y Siemens.
4. Validar diagnóstico Siemens con hardware.
5. Validar adquisición y calidad SCADA.
6. Comprobar consultas, dashboards y datos obsoletos.
7. Robustecer recomendaciones y persistencia.
8. Validar el recorrido completo desde el equipo hasta InfluxDB, API, Grafana y recomendaciones.
9. Ajustar intervalos, carga y cardinalidad.
10. Completar resultados y documentación académica con evidencias.

Hay carencias concretas que deben entrar en la planificación de consolidación:
- API sin autenticación/autorización.
- Configuración de targets con credenciales almacenadas y devueltas sin separación adecuada.
- Validación insuficiente de configuraciones por protocolo.
- Interpolación directa de parámetros en Flux.
- Inserción de datos en HTML que requiere revisar escape y XSS.
- Dependencias de Internet relevantes para redes OT aisladas.
- Dependencias e imágenes no totalmente fijadas.

Propón soluciones proporcionadas al alcance acordado, diferenciando lo necesario para el prototipo de lo exigible a un despliegue industrial.

# 17. Memoria académica y documentación

Documentos relevantes:
- docs/Documentacion_completa_Control_System_Health_Status.md.
- docs/Anteproyecto_PFG_contenido.md.
- docs/Memoria_PFG_contenido.md.
- docs/TFG_Indice_y_Estado_del_Arte.md.
- Memoria pfg_final.docx.
- Otras versiones Word de la memoria.
- Memoria_Previo.pdf.
- Plantilla oficial de memoria.
- Anteproyecto.

No des por terminada la memoria porque un archivo se llame “final”.

Quedan apartados incompletos o de plantilla en distintas versiones:
- Desarrollo técnico.
- Resultados.
- Validación.
- Conclusiones.
- Implicaciones éticas.
- Figuras, tablas, índices y anexos.
- Referencias.

La memoria debe explicar:
- Problema y contexto.
- Objetivos.
- Estado del arte.
- Alternativas y decisiones.
- Arquitectura.
- Implementación.
- Metodología.
- Pruebas.
- Resultados demostrados.
- Limitaciones.
- Conclusiones relacionadas con los objetivos.
- Trabajo futuro.

La documentación académica debe ser clara, coherente, trazable y preferentemente impersonal.

Hay contradicciones documentales que debes conservar como cuestiones abiertas hasta confirmarlas:
- Alcance final.
- Numeración de fases.
- Validación en producción.
- Estado de integración corporativa.
- Versiones de dependencias.
- Número de tests.
- Datos de portada, titulación y convocatoria.
- Documento de memoria que debe considerarse principal.

No inventes resultados, fechas, identidad académica, porcentajes de mejora ni cumplimiento normativo.

# 18. Estado de Git y precauciones de continuidad

En la revisión usada para elaborar este contexto:
- La rama era develop.
- Estaba un commit por delante de origin/develop.
- Había numerosos cambios locales y archivos sin seguimiento.
- SCADA, recomendaciones, pruebas y documentación reciente formaban parte de ese trabajo local.
- También había borrados locales de documentos previamente versionados.

Vuelve a comprobar este estado.

Clonar únicamente el último commit puede no reproducir lo que existe en esta máquina.

Preserva el trabajo local:
- No sobrescribas cambios ajenos.
- No reviertas eliminaciones sin investigar.
- No limpies archivos sin seguimiento.
- No uses comandos destructivos para dejar el árbol “limpio”.
- No hagas commit, push ni cambios de rama salvo petición explícita.

# 19. Qué necesito de ti al retomar

Primero:
1. Revisa instrucciones, documentación y estado del repositorio.
2. Resume brevemente qué entiendes del proyecto.
3. Señala diferencias importantes entre este contexto y el código actual.
4. Identifica el siguiente hito prioritario y sus dependencias.
5. Pregúntame qué objetivo concreto queremos abordar si todavía no lo he indicado.

Después, trabaja sobre el objetivo acordado hasta completar su implementación, verificación y documentación correspondientes.

Mantén siempre una visión conjunta: este proyecto combina plataforma técnica, integración industrial, validación y memoria académica.
