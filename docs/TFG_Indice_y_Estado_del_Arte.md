# TFG — Control System Health Status
## Sistema de Monitorización de Salud para Entornos OT Industriales

**Autor:** Jin Wen Cheng  
**Tutor:** [Nombre del tutor]  
**Universidad:** Universidad Francisco de Vitoria  
**Titulación:** [Grado en Ingeniería Informática / Sistemas]  
**Curso académico:** 2025–2026  
**Empresa colaboradora:** GEA Process Engineering  

---

---

# ÍNDICE

1. [Introducción](#1-introducción)  
   1.1 Motivación y contexto  
   1.2 Objetivos del proyecto  
   1.3 Alcance y limitaciones  
   1.4 Estructura del documento  

2. [Estado del arte](#2-estado-del-arte)  
   2.1 Monitorización de infraestructura IT tradicional  
   2.2 Sistemas de control industrial (SCADA, DCS, HMI)  
   2.3 Protocolos de comunicación industrial  
   2.4 Convergencia IT/OT: retos y oportunidades  
   2.5 Soluciones comerciales de monitorización OT  
   2.6 Bases de datos de series temporales  
   2.7 Contenedorización y despliegue en entornos industriales  
   2.8 Conclusiones del estado del arte  

3. [Análisis y requisitos](#3-análisis-y-requisitos)  
   3.1 Descripción del entorno GEA Process Engineering  
   3.2 Requisitos funcionales  
   3.3 Requisitos no funcionales  
   3.4 Casos de uso principales  

4. [Diseño del sistema](#4-diseño-del-sistema)  
   4.1 Arquitectura general  
   4.2 Justificación y selección de tecnologías  
   4.3 Diseño de la capa de agentes  
   4.4 Diseño del almacenamiento de datos  
   4.5 Diseño de la API REST  
   4.6 Configuración dinámica de targets  
   4.7 Diseño de los dashboards de visualización  

5. [Implementación](#5-implementación)  
   5.1 Estructura del proyecto y organización del código  
   5.2 Librería compartida (`shared/`)  
   5.3 Agente de servidores Windows y VMware (Fase 1)  
   5.4 Agente Siemens PLC (Fase 2)  
   5.5 API REST con FastAPI  
   5.6 Integración con Grafana  
   5.7 Despliegue con Docker Compose  

6. [Validación y pruebas](#6-validación-y-pruebas)  
   6.1 Entorno de pruebas  
   6.2 Pruebas de conectividad y pre-vuelo  
   6.3 Pruebas funcionales por agente  
   6.4 Pruebas de configuración dinámica  
   6.5 Pruebas de resiliencia (target inalcanzable)  

7. [Conclusiones y trabajo futuro](#7-conclusiones-y-trabajo-futuro)  
   7.1 Conclusiones  
   7.2 Objetivos alcanzados  
   7.3 Trabajo futuro  

8. [Bibliografía](#8-bibliografía)  

**Anexo A** — Guía de instalación y puesta en marcha  
**Anexo B** — Manual de uso de la API (referencia de endpoints)  
**Anexo C** — Diagramas de arquitectura  
**Anexo D** — Glosario de términos OT/IT  

---

---

# 1. INTRODUCCIÓN

## 1.1 Motivación y contexto

> **[RELLENAR]** Describe el problema real: GEA gestiona instalaciones industriales en múltiples plantas. Los equipos (servidores Windows, hipervisores ESXi, PLCs Siemens) carecen de una visión unificada de salud. Ante un fallo, el diagnóstico es manual y reactivo. El proyecto nace de la necesidad de un sistema de observabilidad proactivo, independiente del SCADA, que funcione sin modificar la infraestructura existente.

## 1.2 Objetivos del proyecto

> **[RELLENAR]** Lista los objetivos principales:
> - Objetivo general: desarrollar un sistema modular de monitorización de salud para entornos OT industriales.
> - Objetivos específicos: implementar agentes de recolección por protocolo (SNMP, WinRM, pyVmomi, OPC UA, Snap7), diseñar una API REST para configuración dinámica, integrar con Grafana para visualización en tiempo real, etc.

## 1.3 Alcance y limitaciones

> **[RELLENAR]** Qué entra y qué queda fuera. Por ejemplo: el sistema es de solo lectura (no actúa sobre los equipos), se limita a los protocolos implementados en las fases 1 y 2, no incluye autenticación de usuarios en esta versión.

## 1.4 Estructura del documento

> **[RELLENAR]** Párrafo breve explicando qué contiene cada capítulo.

---

---

# 2. ESTADO DEL ARTE

## 2.1 Monitorización de infraestructura IT tradicional

La monitorización de sistemas informáticos es una disciplina madura con décadas de evolución. Las herramientas actuales pueden clasificarse en tres generaciones:

**Primera generación — herramientas basadas en polling activo (1990s–2000s)**  
Nagios (1999) estableció el paradigma de check plugins: cada servicio o host se comprueba periódicamente mediante scripts. Su arquitectura es simple pero no escala bien en entornos con miles de nodos. Icinga, fork de Nagios (2009), introdujo mejoras de rendimiento y una API REST más moderna. Ambas siguen siendo referencia en entornos conservadores.

**Segunda generación — plataformas todo-en-uno (2000s–2010s)**  
Zabbix (2001, open source desde 2004) y PRTG Network Monitor (Paessler, 1997) unificaron recolección, almacenamiento y visualización. Zabbix introdujo el concepto de *proxy* para monitorización de redes remotas, relevante en entornos multi-planta. Sin embargo, ambas herramientas están orientadas a infraestructura IT (servidores, redes) y presentan limitaciones importantes en entornos OT: no soportan de forma nativa protocolos como OPC UA o S7Comm, y su modelo de datos relacional no es óptimo para series temporales de alta frecuencia.

**Tercera generación — observabilidad cloud-native (2010s–presente)**  
Prometheus (SoundCloud, 2012; CNCF 2016) popularizó el modelo *pull* con scraping HTTP y un lenguaje de consultas propio (PromQL). Su integración con Grafana se ha convertido en el estándar de facto para visualización en entornos DevOps. Sin embargo, Prometheus no está diseñado para retención de datos a largo plazo ni para protocolos industriales.

> **[COMPLETAR]** Puedes añadir: comparativa de retención de datos, escalabilidad, soporte de protocolos OT, y por qué ninguna de estas herramientas cubre completamente el caso de uso industrial de GEA.

---

## 2.2 Sistemas de control industrial (SCADA, DCS, HMI)

Los sistemas de control industrial han incorporado capacidades de monitorización de proceso desde su origen, pero con un enfoque radicalmente distinto al de la observabilidad IT.

**SCADA (Supervisory Control and Data Acquisition)**  
Los sistemas SCADA (Wonderware/AVEVA, Ignition de Inductive Automation, WinCC de Siemens) están diseñados para supervisar y controlar el proceso productivo: temperaturas, presiones, caudales, estados de válvulas. Su fortaleza es la integración con el proceso; su limitación, para el objetivo de este TFG, es que no monitorizan la salud del propio sistema informático que los soporta (CPU del servidor SCADA, estado de la VM, salud del PLC como dispositivo).

**DCS (Distributed Control System)**  
Los DCS (ABB System 800xA, Emerson DeltaV, Honeywell Experion) están orientados a procesos continuos de alta fiabilidad. Incluyen diagnósticos de hardware propios pero propietarios, sin API estándar para integración externa.

**Limitación común:** ningún SCADA/DCS proporciona una vista unificada de salud de la infraestructura subyacente (hipervisores, redes, estado de los propios controladores como dispositivos de red). Esta brecha es precisamente la que cubre este proyecto.

> **[COMPLETAR]** Puedes mencionar la diferencia entre monitorización de *proceso* (SCADA) y monitorización de *infraestructura* (este proyecto). También el concepto de "salud del sistema de control" vs "variables de proceso".

---

## 2.3 Protocolos de comunicación industrial

La heterogeneidad de protocolos es uno de los principales retos en entornos OT industriales.

**OPC UA (OPC Unified Architecture)**  
Desarrollado por la OPC Foundation (2008), OPC UA es el estándar de interoperabilidad industrial más relevante de la actualidad. A diferencia de su predecesor OPC Classic (basado en COM/DCOM de Windows), OPC UA es multiplataforma, seguro (X.509, TLS) y orientado a servicios. Siemens lo soporta nativamente en S7-1500 desde firmware V2.0 (puerto 4840). Su modelo de información jerárquico permite descubrir nodos sin conocer la estructura a priori, lo que facilita la integración genérica.

**S7Comm / S7Comm-Plus**  
Protocolo propietario de Siemens (puerto TCP 102) presente en toda la gama S7 (S7-300, S7-400, S7-1200, S7-1500). No requiere licencia en modo lectura y permite acceso directo a bloques de datos (DB) y a la información de sistema (SZL — System Zustands Liste). La librería `python-snap7` proporciona un wrapper Python sobre la librería nativa `snap7.dll`/`libsnap7.so`.

**SNMP (Simple Network Management Protocol)**  
Estándar IETF (RFC 1157, SNMPv2c RFC 1901) presente en prácticamente todos los dispositivos de red y servidores. La MIB HOST-RESOURCES (RFC 2790) permite obtener CPU, memoria y discos de cualquier sistema Windows/Linux sin necesidad de agente propietario. Es el protocolo de menor intrusividad para la monitorización de servidores.

**WinRM (Windows Remote Management)**  
Implementación de Microsoft del estándar WS-Management (DMTF). Permite ejecutar comandos PowerShell de forma remota, lo que posibilita obtener métricas no accesibles vía SNMP: offset NTP, estado de servicios Windows, contadores de rendimiento avanzados.

**Modbus TCP / EtherNet/IP / PROFINET**  
> **[COMPLETAR]** Breve descripción de estos protocolos, relevantes para fases futuras del proyecto (agente Rockwell vía EtherNet/IP, agente de red vía PROFINET DCP).

---

## 2.4 Convergencia IT/OT: retos y oportunidades

La convergencia entre los mundos IT (Tecnologías de la Información) y OT (Tecnologías de Operación) es una tendencia consolidada pero compleja.

**Diferencias fundamentales IT vs OT**

| Dimensión | IT | OT |
|---|---|---|
| Prioridad | Confidencialidad → Integridad → Disponibilidad | Disponibilidad → Integridad → Confidencialidad |
| Ciclo de vida | 3–5 años | 15–30 años |
| Actualizaciones | Frecuentes, automatizadas | Excepcionales, planificadas con parada |
| Tolerancia a latencia | Alta | Baja (tiempo real) |
| Acceso remoto | Habitual | Restringido o inexistente |
| Protocolos | TCP/IP estándar | Propietarios o estándares industriales |

**Iniciativas de estandarización**  
La norma IEC 62443 (Industrial Automation and Control Systems Security) establece un marco de seguridad para entornos OT que incluye requisitos de monitorización y auditoría. La arquitectura Purdue Model (ISA-95) define los niveles de la pirámide de automatización y los flujos de información entre ellos, siendo relevante para entender dónde se ubica este sistema (nivel 3.5, entre MES y SCADA).

> **[COMPLETAR]** Puedes añadir el concepto de "zona desmilitarizada industrial" (IDMZ), y cómo el sistema de este TFG opera en modo solo-lectura para minimizar el impacto en la red OT.

---

## 2.5 Soluciones comerciales de monitorización OT

En los últimos años han aparecido plataformas específicas de monitorización y seguridad OT:

**Plataformas de seguridad OT (asset visibility)**  
- **Claroty**: descubrimiento pasivo de activos OT mediante análisis de tráfico de red (DPI). Orientado a seguridad y cumplimiento normativo. Coste elevado, requiere acceso a puertos SPAN.
- **Nozomi Networks**: similar a Claroty, con énfasis en detección de anomalías mediante IA. 
- **Dragos**: orientado a threat intelligence y respuesta a incidentes en infraestructuras críticas.

Estas plataformas tienen un enfoque de seguridad (¿qué dispositivos hay? ¿hay comportamientos anómalos?) más que de observabilidad operativa (¿está el PLC en RUN? ¿cuánta CPU consume el servidor SCADA?).

**Plataformas de monitorización de proceso**  
- **OSIsoft PI System (ahora AVEVA PI)**: el estándar histórico para historian de datos de proceso en industria. Excelente para datos de planta, pero orientado a variables de proceso, no a métricas de infraestructura. Coste de licencia muy elevado.
- **InfluxDB + Grafana (open source)**: stack que ha ganado adopción en entornos industriales por su flexibilidad, coste cero y soporte de series temporales de alta frecuencia. Es la elección de este proyecto.

**Solución interna GEA: Codex**  
> **[RELLENAR]** Describe brevemente la plataforma interna Codex de GEA: qué es, para qué se usa, cómo se integra con este proyecto (registro de targets vía API REST).

---

## 2.6 Bases de datos de series temporales

Los datos de monitorización tienen una naturaleza inherentemente temporal: cada métrica es un valor asociado a un instante de tiempo. Las bases de datos relacionales tradicionales (MySQL, PostgreSQL) no están optimizadas para este patrón de escritura/consulta.

**InfluxDB**  
Desarrollada por InfluxData (2013), InfluxDB es la base de datos de series temporales open source más utilizada. La versión 2.x (utilizada en este proyecto) introduce el lenguaje de consultas **Flux**, que permite transformaciones complejas como agregaciones temporales, pivotado de columnas y joins entre measurements. El modelo de datos se basa en *measurements* (equivalente a tabla), *tags* (dimensiones de baja cardinalidad, indexados) y *fields* (valores numéricos o string).

La elección de InfluxDB 2.7 para este proyecto se justifica por:
- Escritura optimizada para inserción de puntos temporales (millones/segundo)
- Retención de datos configurable por bucket
- Integración nativa como datasource en Grafana
- Despliegue sencillo vía Docker sin dependencias externas

**Alternativas consideradas**

| Base de datos | Ventajas | Por qué no se eligió |
|---|---|---|
| Prometheus | Pull-based, alertas nativas, CNCF | No orientado a retención larga, no soporta escritura desde agentes push directamente |
| TimescaleDB | SQL estándar, extensión de PostgreSQL | Requiere PostgreSQL, más complejidad operativa |
| Victoria Metrics | Muy eficiente, compatible con PromQL | Menor integración con Grafana para Flux queries |
| ClickHouse | Excelente para analíticas | No optimizado para series temporales de baja latencia |

> **[COMPLETAR]** Si has explorado otras opciones durante el proyecto, añádelas aquí.

---

## 2.7 Contenedorización y despliegue en entornos industriales

**Docker y Docker Compose**  
La contenedorización (Docker, 2013) ha transformado el despliegue de software al garantizar reproducibilidad del entorno. En entornos industriales, donde los sistemas operativos pueden ser versiones antiguas de Windows Server o Linux embebido, Docker permite ejecutar el stack de monitorización de forma aislada sin modificar el sistema anfitrión.

Docker Compose facilita la definición declarativa de aplicaciones multi-contenedor. Para este proyecto permite levantar en un único comando InfluxDB, Grafana, los agentes Python y la API REST, con sus dependencias de red y volúmenes persistentes correctamente configuradas.

**Microservicios en OT**  
La arquitectura de microservicios (cada agente en su propio contenedor) aporta beneficios específicos en el contexto industrial:
- **Aislamiento de fallos**: si el agente Siemens falla, el agente de servidores sigue funcionando
- **Actualización independiente**: se puede actualizar un agente sin afectar al resto
- **Escalabilidad**: se puede desplegar múltiples instancias de un agente para grandes instalaciones

> **[COMPLETAR]** Puedes mencionar Kubernetes si quieres proyectar el trabajo futuro, aunque para este TFG se usa Docker Compose por simplicidad.

---

## 2.8 Conclusiones del estado del arte

> **[RELLENAR]** Párrafo de síntesis que justifique las decisiones de diseño del proyecto a partir del análisis anterior. Estructura sugerida:
>
> - Las herramientas IT tradicionales (Zabbix, Prometheus) no cubren los protocolos industriales necesarios.
> - Las plataformas OT comerciales (Claroty, Nozomi) están orientadas a seguridad, no a observabilidad operativa, y su coste es prohibitivo para un proyecto académico.
> - El stack InfluxDB + Grafana + Python es la opción open source más adecuada para el caso de uso.
> - La arquitectura de agentes independientes por protocolo (SNMP, WinRM, OPC UA, Snap7) es la más flexible para la heterogeneidad de GEA.
> - La configuración dinámica vía API REST es necesaria para integrarse con la plataforma interna Codex de GEA sin reinicios del sistema.

---

---

# 3. ANÁLISIS Y REQUISITOS

## 3.1 Descripción del entorno GEA Process Engineering

> **[RELLENAR]** Describe brevemente GEA: sector (industria alimentaria/farmacéutica/química), tipo de instalaciones, número de plantas, tecnología utilizada (VMs ESXi, servidores Windows, PLCs Siemens). Puede ser a nivel general sin revelar información confidencial.

## 3.2 Requisitos funcionales

> **[RELLENAR]** Lista numerada de requisitos funcionales. Ejemplos:
> - RF-01: El sistema deberá recopilar métricas de CPU, RAM y disco de servidores Windows mediante SNMP sin necesidad de instalar agentes en los servidores monitorizados.
> - RF-02: El sistema deberá obtener el estado de hipervisores ESXi y máquinas virtuales mediante la API vSphere.
> - RF-03: El sistema deberá detectar el estado operativo (RUN/STOP/FAULT) de PLCs Siemens mediante OPC UA o S7Comm.
> - RF-04: El sistema deberá permitir añadir o eliminar targets de monitorización en tiempo de ejecución sin reiniciar los agentes.
> - RF-05: El sistema deberá visualizar los datos en dashboards Grafana con actualización en tiempo real.
> - RF-06: El sistema deberá exponer una API REST para consulta de métricas y gestión de configuración.

## 3.3 Requisitos no funcionales

> **[RELLENAR]** Ejemplos:
> - RNF-01 (Disponibilidad): el sistema deberá reiniciarse automáticamente tras un fallo sin intervención manual (restart: unless-stopped).
> - RNF-02 (Resiliencia): un target inalcanzable no deberá impedir la recolección del resto de targets.
> - RNF-03 (No intrusividad): el sistema solo realizará operaciones de lectura sobre los equipos monitorizados.
> - RNF-04 (Portabilidad): el sistema deberá poder desplegarse en cualquier host con Docker instalado.
> - RNF-05 (Extensibilidad): la arquitectura deberá permitir añadir nuevos tipos de agentes sin modificar el código existente.

## 3.4 Casos de uso principales

> **[RELLENAR]** Diagrama o descripción de los casos de uso más relevantes. Actores: Operador GEA, Sistema Codex, Agente de monitorización.

---

---

# 4. DISEÑO DEL SISTEMA

*(Secciones por desarrollar en la fase de escritura de la memoria)*

## 4.1 Arquitectura general
## 4.2 Justificación y selección de tecnologías
## 4.3 Diseño de la capa de agentes
## 4.4 Diseño del almacenamiento de datos
## 4.5 Diseño de la API REST
## 4.6 Configuración dinámica de targets
## 4.7 Diseño de los dashboards de visualización

---

# 5. IMPLEMENTACIÓN

*(Secciones por desarrollar)*

---

# 6. VALIDACIÓN Y PRUEBAS

*(Secciones por desarrollar)*

---

# 7. CONCLUSIONES Y TRABAJO FUTURO

## 7.1 Conclusiones
## 7.2 Objetivos alcanzados
## 7.3 Trabajo futuro

> **[SUGERENCIAS para trabajo futuro]**
> - Fase 3: agente Rockwell (pylogix, EtherNet/IP)
> - Fase 4: agente de red (SNMP + PROFINET DCP)
> - Fase 5: alertas (Grafana Alerting → email/Teams) y generación de informes PDF
> - Autenticación y control de acceso en la API REST (OAuth2 / JWT)
> - Despliegue en Kubernetes para instalaciones de múltiples plantas

---

---

# 8. BIBLIOGRAFÍA

> **[RELLENAR]** Formato APA o el que indique tu universidad. Referencias sugeridas:

[1] OPC Foundation. (2017). *OPC Unified Architecture Specification Part 1: Overview and Concepts*. OPC Foundation.

[2] IEC. (2018). *IEC 62443-3-3: Industrial communication networks – Network and system security – Part 3-3: System security requirements and security levels*. International Electrotechnical Commission.

[3] Influxdata. (2023). *InfluxDB 2.x Documentation*. Recuperado de https://docs.influxdata.com/influxdb/v2/

[4] Grafana Labs. (2024). *Grafana Documentation*. Recuperado de https://grafana.com/docs/

[5] Snap7 Project. (2023). *Snap7 — A free, open source, multi-platform Siemens S7 Communication library*. Recuperado de http://snap7.sourceforge.net/

[6] Python Software Foundation. (2024). *asyncua — Python OPC-UA client and server library*.

[7] Zabbix. (2024). *Zabbix Documentation 6.4*. Recuperado de https://www.zabbix.com/documentation/

[8] Dragos. (2023). *Year in Review: ICS/OT Cybersecurity*. Dragos Inc.

[9] Purdue University / ISA. *ANSI/ISA-95.00.01: Enterprise-Control System Integration Part 1: Models and Terminology*.

[10] Docker Inc. (2024). *Docker Compose documentation*. Recuperado de https://docs.docker.com/compose/

> **[AÑADIR]** Referencias específicas de los papers/libros que hayas consultado para el estado del arte y el diseño del sistema.

---

---

# ANEXO A — Guía de instalación y puesta en marcha

> **[RELLENAR]** Paso a paso para desplegar el sistema desde cero. Basarte en el CLAUDE.md del proyecto.

---

# ANEXO B — Referencia de endpoints de la API REST

> **[RELLENAR]** Tabla con todos los endpoints, método HTTP, parámetros y ejemplo de respuesta. Puedes exportarlo desde Swagger en `http://localhost:8000/docs`.

---

# ANEXO C — Diagramas de arquitectura

> **[RELLENAR]** Diagrama de componentes, diagrama de flujo de datos, diagrama de secuencia para la configuración dinámica (POST → ConfigPoller → APScheduler → InfluxDB).

---

# ANEXO D — Glosario

| Término | Definición |
|---|---|
| OT | Operational Technology — tecnología que gestiona procesos físicos industriales |
| IT | Information Technology — tecnología de procesamiento de información |
| SCADA | Supervisory Control and Data Acquisition |
| PLC | Programmable Logic Controller |
| HMI | Human-Machine Interface |
| DCS | Distributed Control System |
| OPC UA | Open Platform Communications Unified Architecture |
| SZL | System Zustands Liste — lista de estado del sistema en PLCs Siemens |
| MIB | Management Information Base — base de objetos SNMP |
| ESXi | Hypervisor de VMware para virtualización de servidores |
| API REST | Application Programming Interface de tipo Representational State Transfer |
| Flux | Lenguaje de consultas funcional de InfluxDB 2.x |
| Time-series | Serie temporal — secuencia de valores indexados por tiempo |
| Measurement | Unidad de almacenamiento en InfluxDB, equivalente a tabla |
| Tag | Dimensión de baja cardinalidad en InfluxDB, indexada |
| Field | Valor de medición en InfluxDB, no indexado |
| Docker | Plataforma de contenedorización de aplicaciones |
| APScheduler | Advanced Python Scheduler — librería de tareas periódicas en Python |
