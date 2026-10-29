# Documentación completa del proyecto TFG Control System Health Status

## 1. Contexto del proyecto en GEA y necesidad de monitorización

GEA Process Engineering opera en un entorno industrial en el que conviven activos de tecnología de la información (IT) y de tecnología de operación (OT). En este contexto, la continuidad de servicio no depende únicamente de los equipos de planta, sino también de la infraestructura digital que sostiene los procesos de supervisión, almacenamiento, historización, comunicaciones y visualización.

Dentro de esa infraestructura aparecen varios niveles técnicos que deben entenderse de forma conjunta: servidores Windows, hipervisores VMware ESXi, máquinas virtuales, PLCs y plataformas SCADA. Todos ellos participan, directa o indirectamente, en la ejecución del sistema de control industrial. Una degradación en cualquiera de estas capas puede traducirse en pérdida de visibilidad, fallos de comunicación, indisponibilidad de aplicaciones críticas o incluso interrupciones operativas.

La necesidad del proyecto surge, por tanto, de disponer de una solución unificada que permita conocer el estado de salud del sistema de control sin depender de una única marca o fabricante. El objetivo no es intervenir sobre la planta, sino observarla de forma no intrusiva, registrar métricas homogéneas y ofrecer una base técnica para diagnóstico, mantenimiento y validación futura en entorno real.

## 2. Sistema de servidores y máquinas virtuales de GEA: justificación técnica de la monitorización

En el escenario planteado por GEA, la infraestructura de servidores constituye la base de ejecución de múltiples servicios industriales y auxiliares. Sobre esta capa pueden residir aplicaciones SCADA, historizadores, servicios de comunicaciones, bases de datos, pasarelas de integración o software de ingeniería. Por ello, la salud de los servidores no puede separarse de la salud global del sistema de control.

La monitorización de **servidores Windows** se justifica porque estos equipos suelen alojar software crítico para operación y supervisión. Su degradación puede afectar al rendimiento de aplicaciones OT, a la adquisición de datos y a la disponibilidad de interfaces de operación. El proyecto monitoriza esta capa mediante SNMP y WinRM.

Las métricas Windows implementadas aportan información sobre:

- uso de CPU;
- número de núcleos;
- memoria total, usada y porcentaje de ocupación;
- tiempo de actividad;
- desviación temporal del reloj;
- disponibilidad del host (`reachable`);
- uso de discos por unidad lógica;
- estado de servicios críticos.

La monitorización de **VMware ESXi** es relevante porque el hipervisor representa la capa física-lógica sobre la que se ejecutan múltiples cargas virtualizadas. Un problema en ESXi puede afectar simultáneamente a varias aplicaciones de supervisión o control. Por esta razón, el proyecto incorpora soporte para hosts ESXi dentro del `server-agent`, tratándolos como parte de la infraestructura de servidores de la plataforma OT.

Las métricas ESXi implementadas permiten conocer:

- carga de CPU en MHz y en porcentaje;
- memoria total, usada y porcentaje de uso;
- tiempo de actividad del host;
- estado de conexión;
- modo mantenimiento;
- número de máquinas virtuales alojadas;
- disponibilidad del host.

La monitorización de **máquinas virtuales** aporta una visión más cercana al servicio real que consume la operación. Aunque el host físico esté disponible, una máquina virtual concreta puede estar apagada, degradada o presentar problemas internos. Por ello, el sistema distingue explícitamente entre salud del hipervisor y salud de las VMs.

Las métricas de VM actualmente implementadas incluyen:

- estado de encendido;
- indicador `is_powered_on`;
- consumo de CPU;
- consumo de memoria;
- memoria ballooning;
- tiempo de actividad;
- estado de VMware Tools;
- número de snapshots;
- antigüedad del snapshot más antiguo;
- disponibilidad.

## 3. Arquitectura general del sistema

La solución desarrollada sigue una arquitectura modular orientada a observabilidad OT. Cada dominio tecnológico se encapsula en un agente especializado, mientras que la persistencia, consulta y visualización se centralizan en componentes comunes.

La arquitectura lógica puede resumirse de la siguiente manera:

**Targets industriales o de infraestructura** → **Collectors** → **Schedulers de agente** → **InfluxWriter** → **InfluxDB** → **API FastAPI / Grafana / UI web**.

Este diseño separa claramente la adquisición de datos del almacenamiento y de la explotación posterior. Como consecuencia, el sistema facilita la extensibilidad, reduce el acoplamiento entre protocolos y permite incorporar nuevos tipos de activos sin reescribir la base existente.

## 4. Componentes implementados

### 4.1. Componente `shared`

La librería `shared` concentra los elementos reutilizables por la API y por todos los agentes. Su función es actuar como contrato común del sistema.

Actualmente incluye:

- modelos de datos tipados mediante `dataclasses` para servidores, VMware, Siemens y SCADA;
- modelo base de métrica con `source_id`, `source_type`, `collected_at` y `reachable`;
- `InfluxWriter` como punto único de escritura en InfluxDB;
- `ConfigPoller` para actualización dinámica de targets;
- `Settings` por variables de entorno;
- utilidades de logging.

La decisión de centralizar la escritura en `InfluxWriter` evita inconsistencias de medición, de precisión temporal y de formato entre agentes. Además, la utilización de dataclasses reduce errores de contrato entre collectors y schedulers.

### 4.2. API y UI

La API está implementada con **FastAPI** y constituye la capa de gestión y consulta del sistema. Sus responsabilidades principales son:

- exponer un endpoint de salud del servicio;
- gestionar altas, bajas, consulta y actualización de targets;
- servir de punto de consulta de métricas para servidores, VMware, PLCs y SCADA;
- abstraer las consultas Flux mediante `InfluxQueryService`;
- mantener persistencia de targets en SQLite mediante SQLModel.

La interfaz web incluida en `/ui` permite gestionar targets desde navegador. En su estado actual, soporta formularios para targets `server`, `siemens` y `scada`, con campos específicos para SNMP, WinRM, VMware, OPC UA, Snap7 y listas de tags SCADA.

La combinación API + UI cumple un requisito central del proyecto: modificar el parque monitorizado sin editar ficheros locales ni reiniciar contenedores.

### 4.3. `server-agent`

El `server-agent` implementa la monitorización de infraestructura Windows y VMware. Carga targets dinámicamente desde la API y crea un job por target mediante APScheduler.

Los collectors actualmente integrados son:

- `WindowsSNMPCollector`;
- `WindowsWinRMCollector`;
- `VMwareCollector`.

El scheduler escribe en las mediciones `server_health`, `disk_health`, `service_health`, `esxi_health` y `vm_health`.

### 4.4. `siemens-agent`

El `siemens-agent` monitoriza PLCs Siemens de forma no intrusiva. Su lógica soporta tres modos de recolección:

- `opcua`;
- `snap7`;
- `auto`.

En modo `auto`, el scheduler intenta primero OPC UA y, si el PLC no resulta accesible por esa vía y existe configuración alternativa, usa Snap7 como mecanismo de respaldo. Esta decisión aporta flexibilidad frente a instalaciones heterogéneas y diferencias de configuración entre equipos reales.

La salida del agente se almacena en la medición `siemens_plc_health`.

### 4.5. `scada-agent`

El `scada-agent` constituye una ampliación relevante del alcance del proyecto. Su objetivo no es monitorizar el PLC como controlador, sino leer tags de proceso expuestos por un servidor SCADA compatible con OPC UA.

Se ha separado del `siemens-agent` por una razón arquitectónica clara: ambos utilizan OPC UA, pero el dominio funcional es distinto. El agente Siemens produce una métrica de salud por controlador, mientras que el agente SCADA genera una colección de métricas por tag.

Las capacidades implementadas son:

- conexión a endpoint OPC UA con credenciales opcionales;
- configuración manual o autodetección heurística del tipo de SCADA;
- lectura de tags definidos por `name` y `node_id`;
- separación tipada de valores numéricos, textuales y booleanos;
- devolución de una métrica `BAD` por tag cuando falla toda la conexión;
- escritura en la medición `scada_tag_health`.

La autodetección actual distingue de forma heurística entre Ignition, WinCC, FactoryTalk y AVEVA a partir de textos y metadatos expuestos por el servidor OPC UA. Esta capacidad está desarrollada, pero todavía pendiente de validación con plataformas reales.

### 4.6. InfluxDB

**InfluxDB 2.7** se utiliza como base de datos de series temporales. Su función es almacenar todas las mediciones de salud de forma homogénea y con precisión temporal en segundos.

El proyecto ha normalizado la escritura a través de `InfluxWriter`, lo que evita que cada agente genere consultas o formatos de persistencia distintos. Esta decisión también simplifica el testing y el mantenimiento.

### 4.7. Grafana

**Grafana** actúa como capa de visualización. En la infraestructura del repositorio existen dashboards provisionados para:

- salud de servidores;
- salud de PLCs Siemens;
- tags SCADA.

En el caso de SCADA, el dashboard disponible es una base funcional inicial. Sirve para observar último valor, calidad, reachability y series numéricas, pero todavía requiere refinamiento una vez existan datos reales de planta.

### 4.8. Docker y Docker Compose

El despliegue reproducible se resuelve mediante **Docker Compose**. En el archivo `docker-compose.yml` se definen actualmente los servicios:

- `influxdb`;
- `grafana`;
- `api`;
- `server-agent`;
- `siemens-agent`;
- `scada-agent`;
- `snmpd-sim` como apoyo local de desarrollo.

Los agentes `rockwell-agent` y `network-agent` aparecen reservados como fases futuras, pero no están activos en el despliegue actual.

## 5. Flujo de datos implementado

El flujo de datos del sistema es uniforme en todos los agentes y constituye uno de los principales aciertos del diseño.

1. Un target se registra en la API con un `agent_type` y una `config` específica.

2. El agente correspondiente consulta periódicamente `/config/targets?agent_type=<tipo>` mediante `ConfigPoller`.

3. El scheduler crea o elimina trabajos de APScheduler sin reiniciar el contenedor.

4. En cada ciclo, el collector ejecuta la adquisición de datos sobre el activo objetivo.

5. El resultado se transforma en una dataclass de dominio, o en una lista de dataclasses en el caso SCADA.

6. El scheduler convierte esa salida al contrato de medición y delega la escritura en `InfluxWriter`.

7. InfluxDB almacena los puntos temporales.

8. La API consulta InfluxDB mediante Flux para exponer datos latest o históricos.

9. Grafana consume InfluxDB para visualización, y la UI web consume la API para configuración.

Este flujo homogéneo resulta especialmente valioso para testing, ya que permite validar la lógica funcional de cada capa con mocks, sin depender de hardware físico real.

## 6. Configuración dinámica de targets

Uno de los requisitos funcionales más importantes del proyecto era evitar configuraciones estáticas en los agentes. Este requisito se ha resuelto mediante la combinación de FastAPI, SQLite/SQLModel y `ConfigPoller`.

Cada target se almacena con los campos principales `id`, `plant`, `agent_type`, `display_name`, `enabled` y `config`. El campo `config` se serializa como JSON, lo que permite almacenar parámetros distintos según el tipo de activo sin forzar migraciones complejas del modelo de datos.

El mecanismo dinámico funciona así:

- la API persiste el target;
- el agente correspondiente consulta la lista filtrada por `agent_type`;
- si aparece un target habilitado no conocido, el scheduler lo añade;
- si desaparece o se deshabilita, el scheduler elimina su job;
- el cambio queda aplicado en el siguiente ciclo de polling.

Este enfoque evita reinicios, reduce intervención manual y se alinea con entornos industriales donde la continuidad operativa es prioritaria.

## 7. Mediciones Influx y contratos de datos

El sistema ya dispone de un conjunto definido de mediciones temporales. Cada una responde a un contrato explícito entre collector, scheduler y almacenamiento.

### 7.1. `server_health`

Medición principal para servidores Windows.

**Tags principales:** `source_id`, `source_type`, `hostname`, `collection_method`.

**Fields principales:** `cpu_usage_percent`, `cpu_core_count`, `ram_total_gb`, `ram_used_gb`, `ram_usage_percent`, `uptime_seconds`, `clock_offset_ms`, `reachable`.

### 7.2. `disk_health`

Medición secundaria por disco lógico de servidor Windows.

**Tags principales:** `source_id`, `drive_letter`.

**Fields principales:** `total_gb`, `used_gb`, `usage_percent`.

### 7.3. `service_health`

Medición por servicio Windows monitorizado.

**Tags principales:** `source_id`, `service_name`.

**Fields principales:** `state`, `is_running`, `start_mode`.

### 7.4. `esxi_health`

Medición de salud de host VMware ESXi.

**Tags principales:** `source_id`, `source_type`, `hostname`, `version`.

**Fields principales:** `cpu_usage_percent`, `cpu_used_mhz`, `cpu_total_mhz`, `ram_total_gb`, `ram_used_gb`, `ram_usage_percent`, `uptime_seconds`, `connection_state`, `maintenance_mode`, `num_vms`, `reachable`.

### 7.5. `vm_health`

Medición de salud de máquina virtual.

**Tags principales:** `source_id`, `source_type`, `vm_name`, `esxi_host`, `guest_os`.

**Fields principales:** `power_state`, `is_powered_on`, `cpu_usage_mhz`, `ram_usage_mb`, `ram_balloon_mb`, `uptime_seconds`, `tools_status`, `num_snapshots`, `oldest_snapshot_age_days`, `reachable`.

### 7.6. `siemens_plc_health`

Medición de salud de PLC Siemens.

**Tags principales:** `source_id`, `plc_name`, `plant`, `model`, `firmware`, `collection_method`.

**Fields principales:** `reachable`, `cpu_state`, `cpu_state_code`, `load_memory_used_percent`, `work_memory_used_percent`, `cycle_time_ms`, `uptime_seconds`, `battery_ok`, `last_error_code`, `last_error_text`.

### 7.7. `scada_tag_health`

Medición de tags SCADA incorporada en la ampliación más reciente del proyecto.

**Tags principales:** `source_id`, `scada_type`, `tag_name`.

**Fields principales:** `value_float`, `value_string`, `value_bool`, `quality`, `reachable`.

**Field opcional de diagnóstico:** `last_error_text`.

Este contrato evita forzar una representación exclusivamente numérica. Un mismo SCADA puede exponer variables analógicas, estados textuales y señales binarias. La separación en tres campos de valor permite mantener tipado explícito sin perder generalidad.

Además, el diseño actual contempla que un fallo de conexión total genere una métrica por cada tag configurado con `quality = BAD`, `reachable = 0` y sin valor de proceso. Esta decisión mejora la trazabilidad del fallo y su representación posterior en Grafana o en consultas históricas.

## 8. Testing implementado con pytest y resultado actual

El proyecto dispone ya de una suite de testing automatizado con **pytest**. Su objetivo es validar el comportamiento funcional de los componentes sin depender de equipos reales, ni de InfluxDB en ejecución, ni de contenedores Docker levantados durante la prueba.

La cobertura actual incluye, entre otros elementos:

- modelos compartidos;
- `InfluxWriter`;
- `ConfigPoller`;
- collectors de Windows, VMware, Siemens y SCADA;
- schedulers de `server-agent`, `siemens-agent` y `scada-agent`;
- construcción de consultas Flux en `InfluxQueryService`;
- endpoints principales relacionados con SCADA.

En la verificación realizada en el entorno actual del repositorio, el resultado ha sido:

**55 passed, 2 skipped**

Los tests omitidos corresponden a casos condicionados por dependencias del entorno host y no representan un fallo funcional del código probado.

Desde el punto de vista técnico, los tests SCADA ya validan aspectos especialmente importantes:

- separación correcta entre `value_float`, `value_string` y `value_bool`;
- retorno de métricas `BAD` por tag ante fallo total de conexión;
- clasificación heurística de tipo de SCADA;
- escritura en `scada_tag_health` con conversión de `reachable` a entero;
- construcción correcta de queries latest/history sobre la medición SCADA.

## 9. Estado actual del proyecto y pendientes

El estado actual del proyecto puede resumirse de la siguiente forma.

### 9.1. Elementos desarrollados

- arquitectura modular con agentes especializados;
- librería común `shared`;
- API FastAPI con persistencia SQLite;
- UI web para gestión de targets;
- `server-agent` para Windows, ESXi y VMs;
- `siemens-agent` con OPC UA, Snap7 y fallback automático;
- `scada-agent` para tags OPC UA de SCADA;
- almacenamiento en InfluxDB;
- dashboards base en Grafana;
- despliegue por Docker Compose;
- suite automatizada de tests unitarios.

### 9.2. Estado por fases

- **Fase 1 — server-agent (SNMP, WinRM, VMware):** desarrollada, pendiente de validación en producción.
- **Fase 2 — siemens-agent (OPC UA, Snap7):** desarrollada, pendiente de pruebas con hardware real.
- **Ampliación SCADA — scada-agent (OPC UA tags):** desarrollada, pendiente de validación con plataformas SCADA reales.
- **Fase 3 — rockwell-agent (pylogix):** no iniciada.
- **Fase 4 — network-agent (SNMP, scapy):** planificada.
- **Fase 5 — alerting y reporting:** planificada.

### 9.3. Limitaciones actuales

Aunque el sistema ya está implementado de forma funcional y cuenta con validación unitaria sólida, todavía existen limitaciones importantes que deben declararse con honestidad técnica:

- no se ha completado aún una validación integral en entorno industrial real;
- la autodetección de tipo de SCADA es heurística y requiere contraste con productos reales;
- el dashboard SCADA actual es inicial y todavía no ha sido refinado con datos de explotación;
- no se ha ejecutado todavía una prueba end-to-end completa con Docker, OPC UA real, escritura en InfluxDB y validación visual en Grafana;
- los agentes Rockwell y Network no están implementados.

## 10. Próximos pasos de validación real

La siguiente etapa del proyecto debe centrarse en la validación operativa, no en la ampliación inmediata de funcionalidades. Técnicamente, los próximos pasos recomendados son los siguientes.

### 10.1. Validación de infraestructura y despliegue

- levantar el stack completo con Docker Compose;
- verificar conectividad entre agentes, API, InfluxDB y Grafana;
- comprobar persistencia de configuración en SQLite;
- revisar logs y comportamiento de los jobs dinámicos.

### 10.2. Validación con servidores Windows y VMware reales

- registrar targets reales de Windows por SNMP y WinRM;
- contrastar las métricas obtenidas con herramientas nativas del sistema;
- registrar un host ESXi real o de laboratorio;
- comprobar consistencia entre métricas del host y métricas de VMs.

### 10.3. Validación con PLCs Siemens reales

- probar conectividad OPC UA sobre equipos Siemens disponibles;
- validar modo `auto` con escenarios de fallback real hacia Snap7;
- contrastar estados de CPU, memoria y firmware con la información de ingeniería del PLC.

### 10.4. Validación con SCADA real

- crear targets `scada` desde la UI;
- verificar lectura real de tags numéricos, textuales y booleanos;
- comprobar calidad de datos y tratamiento de errores por tag;
- contrastar la autodetección con productos concretos como Ignition, WinCC, FactoryTalk o AVEVA;
- confirmar visualización correcta en Grafana y consulta correcta desde la API.

### 10.5. Validación de rendimiento y operación

- estudiar la cardinalidad generada por listas amplias de tags SCADA;
- ajustar intervalos de polling según impacto operacional;
- definir criterios de selección de tags útiles para operación;
- preparar la futura fase de alerting sobre métricas consolidadas y validadas.

## 11. Conclusión técnica del estado actual

El proyecto ha evolucionado desde una idea de monitorización de salud de infraestructura OT hacia una plataforma modular ya funcional, con separación clara de responsabilidades, contratos de datos consistentes y base de testing automatizado. La solución ya permite gestionar targets dinámicos, adquirir métricas de varias capas tecnológicas y almacenarlas de forma homogénea para consulta y visualización.

No obstante, desde una perspectiva académica y profesional, el trabajo no puede considerarse completamente validado hasta ejecutar pruebas con activos reales de GEA o con entornos de laboratorio representativos. La situación actual es técnicamente sólida en desarrollo y en testing unitario, pero la validación de campo sigue siendo el hito decisivo de la siguiente fase.
