# ANTEPROYECTO PFG — Contenido para Word
## Control System Health Status
### Grado en Ingeniería Informática — Universidad Francisco de Vitoria

> Copia cada sección en tu Word y aplica los estilos de título correspondientes.
> Los textos entre [COMPLETAR] son los únicos que necesitas rellenar tú con datos personales o de empresa.

---

---

# 1. INTRODUCCIÓN

## 1.1. Contexto y Justificación del Proyecto

### El momento de la transformación digital industrial

La industria manufacturera y de procesos vive una de las transformaciones más profundas de su historia. La denominada **Industria 4.0** —término acuñado por el gobierno alemán en 2011 y consolidado como paradigma global en la última década— integra tecnologías como el Internet Industrial de las Cosas (IIoT), la inteligencia artificial, la computación en la nube y la ciberseguridad en el núcleo de los procesos productivos. Esta transformación no es opcional: según el informe *Global Lighthouse Network* del Foro Económico Mundial (2023), las fábricas que han adoptado tecnologías de Industria 4.0 reportan incrementos de productividad de entre el 15 % y el 30 %, reducciones de tiempo de inactividad no planificada de hasta el 50 % y mejoras de calidad de producto del 10 % al 20 %.

En este contexto, la **disponibilidad y fiabilidad de los sistemas informáticos que sustentan la producción** —servidores de control, hipervisores de virtualización, controladores lógicos programables (PLC) y redes industriales— ha pasado de ser una preocupación técnica a convertirse en un factor crítico del negocio. Un fallo en un servidor SCADA o en un PLC puede paralizar una línea de producción entera. En el sector alimentario y farmacéutico, donde los tiempos de inactividad tienen consecuencias directas sobre la calidad del producto, el coste medio de una hora de parada no planificada oscila entre los 50.000 y los 500.000 euros, según el informe *Cost of Downtime* de Aberdeen Research (2022). La capacidad de detectar degradaciones antes de que se conviertan en fallos —lo que en el mundo IT se conoce como **observabilidad proactiva**— es, por tanto, un factor diferencial de competitividad.

### La brecha entre IT y OT

Para comprender el problema que aborda este proyecto, es fundamental distinguir entre dos mundos tecnológicos que, históricamente, han operado de forma separada y que ahora convergen de manera inevitable.

El mundo **IT** (Information Technology) engloba los sistemas informáticos de gestión empresarial: servidores, bases de datos, aplicaciones de negocio, redes corporativas. Es un mundo estandarizado, con protocolos abiertos (TCP/IP, HTTP, SNMP), ciclos de actualización cortos y una cultura de monitorización y observabilidad muy madura.

El mundo **OT** (Operational Technology) engloba los sistemas que controlan los procesos físicos de producción: PLCs, SCADA, DCS, HMI, redes industriales. Es un mundo históricamente propietario, con protocolos específicos de fabricante (S7Comm de Siemens, EtherNet/IP de Rockwell), equipos con ciclos de vida de 15 a 30 años, y una cultura de operación donde la **disponibilidad** es el valor supremo, incluso por encima de la seguridad lógica o la facilidad de gestión.

Esta separación histórica genera un problema concreto: los sistemas de monitorización maduros del mundo IT —Nagios, Zabbix, Prometheus— no hablan los protocolos industriales del mundo OT, y los sistemas SCADA/DCS, aunque supervisan el proceso productivo, no están diseñados para monitorizar su propia infraestructura informática subyacente. El resultado son **puntos ciegos en la observabilidad de las plantas industriales**: nadie sabe, en tiempo real, si el servidor que ejecuta el SCADA está al 95 % de RAM, si el hipervisor ESXi tiene una VM con snapshots de tres meses de antigüedad que está consumiendo disco silenciosamente, o si el PLC que controla la línea de embotellado lleva dos horas en estado de alarma sin que nadie lo haya detectado.

### El papel de la digitalización en la monitorización OT

La convergencia IT/OT ha acelerado la necesidad de una solución a este problema. A medida que los sistemas OT se interconectan con las redes corporativas —impulsados por la necesidad de datos de proceso para analítica, mantenimiento predictivo y trazabilidad— la superficie de exposición de los sistemas industriales crece, y con ella la necesidad de visibilidad. La norma internacional **IEC 62443**, el estándar de referencia para la ciberseguridad industrial, establece explícitamente la monitorización continua de los sistemas de control como uno de los requisitos de seguridad básicos para instalaciones industriales.

Paralelamente, la madurez de tecnologías open source como Docker, InfluxDB y Grafana ha democratizado la construcción de sistemas de monitorización: ya no es necesario depender de soluciones propietarias de alto coste para obtener un sistema robusto, escalable y flexible. Esto abre la puerta a proyectos como el que se describe en este documento: una solución construida con herramientas de código abierto, adaptada específicamente a los protocolos y necesidades del entorno OT industrial.

### Contexto específico: GEA Process Engineering

GEA Process Engineering es una empresa de ingeniería de procesos industriales especializada en tecnología de separación, tratamiento de fluidos y procesado de alimentos, con presencia en instalaciones de producción repartidas por múltiples países. [COMPLETAR: añade 2-3 frases sobre los sectores específicos (alimentario, farmacéutico, etc.) y el número aproximado de plantas o la escala de sus operaciones, sin revelar información confidencial.]

La infraestructura tecnológica de las instalaciones de GEA es representativa de la realidad OT industrial: **servidores Windows** que ejecutan aplicaciones de control, supervisión y SCADA; **hipervisores VMware ESXi** que alojan máquinas virtuales críticas para la operación; y **PLCs de la familia Siemens S7** que gobiernan el control directo de los procesos de producción. Esta infraestructura, distribuida en múltiples plantas, carece actualmente de un sistema unificado de monitorización de salud. El diagnóstico ante un incidente es **manual y reactivo**: un técnico debe conectarse individualmente a cada sistema para evaluar su estado, lo que alarga los tiempos de respuesta e impide la detección temprana de degradaciones.

Adicionalmente, GEA dispone de una plataforma interna de gestión denominada **Codex**, que centraliza la configuración y supervisión de sus instalaciones a nivel corporativo. Cualquier nueva herramienta de monitorización debe ser capaz de integrarse con Codex mediante una API REST estándar, que permita el registro y la eliminación dinámica de activos monitorizados sin interrumpir el servicio.

### Justificación del proyecto y valor añadido

Este Proyecto de Fin de Grado responde directamente a la necesidad identificada: la ausencia de un sistema de monitorización de salud unificado para la infraestructura OT de GEA. La solución propuesta no es únicamente un ejercicio académico: será desplegada en el entorno real de la empresa, aportando valor operativo inmediato.

Los factores que justifican el interés del proyecto son los siguientes:

**Impacto operativo en GEA.** Un sistema de monitorización centralizado permite al equipo de operaciones detectar proactivamente degradaciones en los servidores, hipervisores y PLCs, reduciendo el tiempo medio de detección (MTTD) de incidencias y, en consecuencia, el tiempo de inactividad no planificada. Los dashboards en tiempo real proporcionan una visión unificada de la salud de toda la infraestructura, facilitando la toma de decisiones operativas.

**No intrusividad.** El sistema opera en modo solo lectura, utilizando protocolos de consulta estándar (SNMP GET, OPC UA read, Snap7 PG-connection) sin modificar ninguna configuración de los equipos monitorizados. Esto es un requisito crítico en entornos OT, donde cualquier modificación no planificada puede comprometer la seguridad del proceso.

**Neutralidad de fabricante.** La arquitectura modular por agentes permite cubrir equipos de distintos fabricantes con un único sistema: servidores Windows de cualquier versión, hipervisores VMware ESXi, y PLCs Siemens de las familias S7-300, S7-1200 y S7-1500. El diseño extensible permite incorporar en el futuro PLCs Rockwell y dispositivos de red con cambios mínimos en la arquitectura base.

**Coste cero de licencias.** El stack tecnológico —InfluxDB, Grafana, Python, FastAPI, Docker— es íntegramente open source, eliminando las dependencias de licencias propietarias que caracteriza a las soluciones comerciales equivalentes (OSIsoft PI, Claroty, Nozomi Networks), cuyo coste anual puede superar los 50.000 euros.

**Integración con Codex.** La API REST desarrollada permite a la plataforma interna de GEA registrar, modificar y eliminar targets de monitorización en tiempo real, sin necesidad de reiniciar el sistema. Esta capacidad de reconfiguración dinámica es esencial para una empresa con múltiples plantas en constante evolución.

**Valor académico y transferibilidad.** El proyecto integra de forma real y en producción conocimientos de sistemas distribuidos, protocolos de red industriales, arquitectura de microservicios, bases de datos de series temporales y desarrollo de APIs REST. La arquitectura desarrollada es genérica y transferible a cualquier organización con infraestructura OT heterogénea.

---

## 1.2. Objetivos

### Objetivo general

Diseñar e implementar un sistema de monitorización de salud en tiempo real para infraestructura OT industrial, modular, independiente del fabricante y desplegable mediante contenedores Docker, que permita a GEA Process Engineering supervisar el estado de sus servidores Windows, hipervisores VMware ESXi y PLCs Siemens desde una interfaz unificada, integrándose con su plataforma interna Codex mediante una API REST de configuración dinámica.

### Objetivos específicos

- Analizar los protocolos de comunicación industrial disponibles para la monitorización no intrusiva de infraestructura OT (SNMP, WinRM, OPC UA, S7Comm) y determinar la combinación más adecuada para cada tipo de activo en el entorno GEA.

- Diseñar una arquitectura de software modular basada en microservicios contenedorizados, que separe la responsabilidad de recolección (agentes), almacenamiento (InfluxDB), exposición (API REST) y visualización (Grafana), y que permita añadir nuevos tipos de agentes sin modificar el código existente.

- Implementar una librería compartida en Python que encapsule la lógica común a todos los agentes: escritura en InfluxDB, modelos de datos, configuración por variables de entorno y logging estructurado.

- Implementar un agente de monitorización para servidores Windows mediante SNMP (HOST-RESOURCES-MIB) y WinRM con PowerShell, capaz de recopilar métricas de CPU, memoria, disco, servicios críticos y desviación NTP.

- Implementar un agente de monitorización para entornos de virtualización VMware ESXi mediante la API vSphere (pyVmomi), capaz de reportar el estado de hipervisores y máquinas virtuales, incluyendo detección de snapshots con antigüedad superior a un umbral configurable.

- Implementar un agente de monitorización para PLCs Siemens mediante OPC UA como protocolo principal y S7Comm (Snap7) como fallback automático, capaz de obtener el estado operativo del CPU (RUN/STOP/FAULT), el uso de memoria de carga y de trabajo, y el firmware y número de serie del equipo.

- Desarrollar una API REST con FastAPI que exponga los datos de monitorización a la plataforma Codex de GEA y permita el registro, actualización y eliminación dinámica de targets de monitorización en tiempo de ejecución, persistiendo la configuración en SQLite.

- Integrar la visualización de datos mediante dashboards en Grafana provisionados automáticamente, con paneles de estado por activo, series temporales de métricas clave y alertas visuales por umbral.

- Validar el sistema en el entorno real de GEA, comprobando la correcta recolección de métricas para cada tipo de activo, la resiliencia ante targets inalcanzables, y el correcto funcionamiento de la configuración dinámica sin reinicio de agentes.

---

---

# 2. INVESTIGACIÓN PREVIA

La monitorización de sistemas informáticos es una disciplina técnica consolidada en el ámbito IT, pero su extensión al mundo OT industrial plantea retos específicos que hacen necesario un análisis del estado del arte en varias áreas convergentes: herramientas de monitorización existentes, protocolos de comunicación industriales, bases de datos de series temporales, arquitecturas de microservicios y soluciones comerciales de visibilidad OT. Esta investigación previa sintetiza el conocimiento relevante y justifica las decisiones de diseño del proyecto.

## 2.1 La evolución de las herramientas de monitorización IT

### Primera generación: monitorización basada en checks activos (1990s–2000s)

**Nagios** (Galstad, 1999) [1] estableció el paradigma que dominaría la monitorización IT durante más de una década: un proceso central ejecuta periódicamente *plugins* que verifican el estado de servicios y hosts, y notifica cuando se detectan problemas. Su arquitectura es conceptualmente simple —un binario, un directorio de plugins, un fichero de configuración— pero no escala bien más allá de unos pocos cientos de nodos. **Icinga**, fork de Nagios creado en 2009 [2], introdujo una API REST, soporte de base de datos relacional para el estado y mejoras de rendimiento, pero mantuvo el mismo modelo mental de *check plugin*.

La limitación fundamental de esta generación es que la monitorización se modela como una secuencia de comprobaciones binarias (OK/WARNING/CRITICAL/UNKNOWN), no como un flujo continuo de métricas. Esta visión es insuficiente para el análisis de tendencias y la detección temprana de degradaciones graduales —como un servidor cuya memoria libre decrece lentamente durante días antes de generar un problema real.

### Segunda generación: plataformas todo-en-uno (2000s–2010s)

**Zabbix** (Alexei Vladishev, 2001; open source desde 2004) [3] superó las limitaciones de Nagios al unificar en una sola plataforma la recolección de métricas, el almacenamiento histórico, la visualización y la gestión de alertas. Su arquitectura incluye un servidor central, agentes instalados en los hosts monitorizados (o proxies para redes remotas), y una base de datos relacional (MySQL/PostgreSQL) para el almacenamiento. Zabbix soporta SNMP de forma nativa y, a partir de la versión 6.x, incorporó el agente modular **Zabbix Agent 2** con un plugin nativo de Modbus TCP/RTU, lo que amplió su alcance hacia entornos industriales. La versión **7.0 LTS** (junio 2024) y la 7.2 (diciembre 2024) consolidan esta evolución; la propia empresa lo describe como *"the universal, open-source observability solution for IT & OT"* [3a], con más de 300.000 despliegues en 190 países.

Sin embargo, Zabbix presenta limitaciones importantes para el caso de uso concreto de este proyecto: su soporte OPC UA **no es nativo** —requiere el desarrollo de un plugin externo en Go para Zabbix Agent 2, sin implementación oficial disponible—; el protocolo S7Comm (Siemens) no está soportado de ninguna forma; y su modelo de almacenamiento relacional no está optimizado para el patrón de escritura de alta frecuencia de métricas de proceso. Estas limitaciones justifican un enfoque de agentes Python dedicados con librerías especializadas (asyncua, python-snap7).

**PRTG** (Paessler, 1997) [4] ha evolucionado significativamente hacia el mundo OT. En su versión actual dispone de sensores nativos para **OPC UA**, **Modbus TCP**, **MQTT** y **EtherNet/IP** sin necesidad de middleware adicional, y en 2025 integró su *Multi-Platform Probe* (contenedor Docker ligero) en el ecosistema **Siemens Industrial Edge**, permitiendo desplegar PRTG directamente en hardware de planta de Siemens [4a]. Incluye además una extensión **OPC UA Server** que expone las métricas recopiladas como nodos OPC UA para que los sistemas SCADA puedan consumirlas. Su principal limitación sigue siendo el modelo de licencias por sensor, que puede resultar costoso en instalaciones con miles de puntos de monitorización.

### Tercera generación: observabilidad cloud-native (2010s–presente)

**Prometheus** (SoundCloud, 2012; CNCF 2016) [5] introdujo un cambio de paradigma: en lugar del modelo *push* (el agente envía datos al servidor), Prometheus adopta el modelo *pull* (el servidor hace scraping periódico de un endpoint HTTP `/metrics` expuesto por cada servicio). Este enfoque tiene ventajas en entornos cloud-native —discovery automático mediante etiquetas— pero introduce complejidad en entornos OT donde los dispositivos industriales no exponen endpoints HTTP.

El lenguaje de consultas **PromQL** es potente para operaciones sobre series temporales, pero Prometheus no está diseñado para retención de datos a largo plazo: su almacenamiento local está optimizado para ventanas de días o semanas, no para históricos de meses o años que pueden ser relevantes en análisis de mantenimiento industrial.

**Grafana** [6], desarrollado inicialmente como frontend para Graphite y posteriormente para Prometheus, se ha convertido en el estándar de facto de visualización de métricas. Su capacidad de conectarse a múltiples datasources —InfluxDB, Prometheus, Elasticsearch, bases de datos relacionales— y su sistema de provisioning declarativo desde ficheros YAML/JSON lo hacen ideal para el despliegue automatizado en entornos industriales.

La conclusión de este análisis es que **ninguna de las herramientas IT existentes cubre de forma nativa los protocolos industriales** (OPC UA, S7Comm, EtherNet/IP) ni está adaptada a las restricciones operativas del mundo OT (no intrusividad, entornos sin acceso a Internet, ciclos de vida largos). Esto justifica el desarrollo de agentes específicos sobre un stack de almacenamiento y visualización open source.

---

## 2.2 Sistemas de control industrial y su capacidad de automonitorización

### SCADA y la monitorización de proceso vs. la monitorización de infraestructura

Los sistemas SCADA (Supervisory Control and Data Acquisition) —Ignition de Inductive Automation [7], WinCC de Siemens [8], iFix de GE Digital— están diseñados para supervisar y controlar el proceso productivo: temperaturas, presiones, caudales, estados de válvulas y actuadores. Su fortaleza es precisamente la integración con el proceso; su limitación para el objetivo de este proyecto es que **no monitorizan la salud del sistema informático que los soporta**.

Un sistema WinCC puede mostrar perfectamente el estado de una válvula en la planta mientras el servidor Windows que lo ejecuta está al 98 % de uso de CPU, o mientras el disco del sistema operativo está a punto de llenarse. Esta distinción entre *monitorización de proceso* (qué está pasando en la planta) y *monitorización de infraestructura* (qué estado tienen los sistemas que controlan la planta) es conceptualmente fundamental y es la que define el alcance de este proyecto.

### DCS y los diagnósticos propietarios

Los Sistemas de Control Distribuido (DCS) —ABB System 800xA [9], Emerson DeltaV, Honeywell Experion— incluyen capacidades de diagnóstico de hardware propias: estado de módulos I/O, comunicaciones entre controladores, redundancia de fuentes de alimentación. Sin embargo, estos diagnósticos son propietarios, accesibles únicamente desde las consolas de ingeniería del propio DCS, y no disponen de APIs estándar para su integración con sistemas externos de monitorización.

Esta ausencia de interoperabilidad en los diagnósticos de los sistemas de control es uno de los principales argumentos para justificar una solución basada en protocolos de acceso estándar como OPC UA o SNMP, que permitan extraer información del estado de los equipos sin depender de las interfaces propietarias de cada fabricante.

---

## 2.3 Protocolos de comunicación industrial para monitorización no intrusiva

La elección de los protocolos de comunicación es una de las decisiones de diseño más críticas en un sistema de monitorización OT. Los criterios de selección son: universalidad (soporte por el mayor número posible de dispositivos), no intrusividad (solo lectura, sin modificación de configuración), seguridad (cifrado y autenticación cuando sea posible) y disponibilidad de librerías open source en Python.

### OPC UA (OPC Unified Architecture)

OPC UA (IEC 62541) [10] es el estándar de interoperabilidad industrial más relevante de la actualidad. Desarrollado por la OPC Foundation y publicado en 2008, resuelve los problemas de su predecesor OPC Classic: mientras OPC Classic estaba basado en la tecnología COM/DCOM de Microsoft (solo Windows, sin cifrado, con problemas de firewall), OPC UA es multiplataforma, soporta cifrado TLS 1.2/1.3 y autenticación mediante certificados X.509, y opera sobre TCP estándar (puerto 4840 por defecto).

El modelo de información de OPC UA es jerárquico y autodescriptivo: un cliente puede explorar el espacio de nodos del servidor (browsing) sin conocer a priori su estructura. Cada nodo tiene atributos (NodeId, BrowseName, Value, DataType) que pueden leerse mediante operaciones estándar. Esta capacidad de descubrimiento es especialmente valiosa en un entorno heterogéneo como el de GEA, donde distintos modelos de PLC o distintas versiones de WinCC pueden exponer estructuras de nodos diferentes.

Siemens ha incorporado un servidor OPC UA nativo en la familia S7-1500 desde el firmware V2.0, accesible en el puerto 4840 sin necesidad de software adicional. Este servidor expone el estado del CPU, el árbol de bloques de datos configurados, y nodos de diagnóstico estándar. La plataforma SCADA Ignition de Inductive Automation también expone un servidor OPC UA que agrega los tags de todos los PLCs configurados, proporcionando un único punto de acceso a toda la planta.

La librería Python **asyncua** (versión 1.0.6) [11] implementa el estándar OPC UA en su totalidad, incluyendo cliente y servidor asíncronos basados en asyncio, soporte de certificados y cifrado, y una API Pythónica que facilita el desarrollo de aplicaciones de monitorización.

### S7Comm / Snap7

S7Comm es el protocolo propietario de Siemens para la comunicación con controladores S7 (RFC 1006 / ISO 8073 sobre TCP, puerto 102). Está presente en toda la gama S7 desde los modelos 300 y 400 de los años 1990 hasta los modernos S7-1500, lo que lo convierte en el protocolo con mayor penetración en el parque instalado de PLCs Siemens.

El proyecto open source **Snap7** [12], desarrollado por Davide Nardella, proporciona una librería nativa multiplataforma (Windows/Linux/macOS) que implementa el protocolo S7Comm sin necesidad de instalar software de Siemens. La librería Python **python-snap7** (versión 1.3) es un wrapper de esta librería nativa que facilita el desarrollo en Python.

Para el propósito de monitorización de salud, Snap7 permite acceder a la **SZL** (System Zustands Liste, Lista de Estado del Sistema), un conjunto de estructuras de datos de solo lectura que el PLC mantiene internamente con información de diagnóstico: estado del CPU (RUN/STOP/STARTUP/FAULT), modelo y firmware del módulo, número de serie, uso de memoria de carga y de trabajo, y buffer de diagnóstico con los últimos eventos registrados. El acceso SZL no requiere ninguna configuración adicional en el PLC ni conocimiento de la estructura de los bloques de datos del programa de aplicación.

### SNMP (Simple Network Management Protocol)

SNMP es el protocolo de gestión de red más universal existente, definido por el IETF en los RFC 1157 (SNMPv1, 1988) y RFC 1901 (SNMPv2c, 1996) [13]. Está soportado por prácticamente cualquier dispositivo de red y servidor, independientemente del fabricante o el sistema operativo.

La **MIB HOST-RESOURCES** (RFC 2790) [14] define un conjunto de objetos SNMP para la monitorización de sistemas: procesadores (tabla hrProcessorLoad), memoria y almacenamiento (tabla hrStorageTable), dispositivos instalados (hrDeviceTable) y software instalado (hrSWInstalledTable). Esta MIB es soportada por el servicio SNMP nativo de Windows Server sin necesidad de instalar ningún software adicional, lo que la convierte en la opción de menor intrusividad para la monitorización de servidores Windows.

La limitación de SNMP en el contexto de este proyecto es que no proporciona información sobre servicios Windows específicos (como el estado de un servicio SCADA), el offset de sincronización NTP, o métricas de rendimiento avanzadas. Para obtener estas métricas adicionales se combina con WinRM.

### WinRM (Windows Remote Management)

WinRM es la implementación de Microsoft del estándar WS-Management (DMTF DSP0226, 2013) [15], que permite la gestión remota de sistemas Windows mediante protocolos basados en SOAP/HTTP. La librería Python **pywinrm** [16] implementa un cliente WinRM que permite ejecutar scripts PowerShell de forma remota y obtener su salida.

Esta capacidad permite obtener métricas no accesibles vía SNMP: el estado de servicios Windows específicos (Get-Service), el offset de sincronización NTP del servidor (w32tm /query /status), contadores de rendimiento avanzados (Get-Counter) y el inventario de software instalado. La combinación SNMP (siempre disponible, sin agente) + WinRM (disponible si está habilitado, más información) proporciona una estrategia de monitorización en dos niveles de profundidad.

---

## 2.4 Convergencia IT/OT: marco normativo y arquitectural

### El modelo de referencia Purdue (ISA-95)

El modelo de referencia Purdue, formalizado en el estándar **ANSI/ISA-95** [17], define los niveles de la pirámide de automatización industrial:

- **Nivel 0:** Proceso físico (sensores, actuadores)
- **Nivel 1:** Control básico (PLCs, controladores de proceso)
- **Nivel 2:** Supervisión (SCADA, HMI)
- **Nivel 3:** Operaciones de planta (MES, historian)
- **Nivel 4:** Planificación empresarial (ERP, sistemas corporativos)

El sistema desarrollado en este proyecto opera en el **nivel 3.5** (entre MES y corporativo), monitorizando la infraestructura informática de los niveles 1, 2 y 3 sin interferir en el flujo de control. Esta ubicación arquitectural es relevante para justificar el diseño no intrusivo: el sistema de monitorización no escribe datos en los PLCs ni modifica configuraciones de SCADA, opera únicamente como observador pasivo de la infraestructura.

### IEC 62443: ciberseguridad industrial y la necesidad de monitorización

La norma **IEC 62443** [18] es el estándar internacional de referencia para la ciberseguridad de Sistemas de Automatización y Control Industrial (IACS). Su parte 3-3 (*System security requirements and security levels*) establece requisitos de seguridad organizados en cuatro niveles (SL 1–4). Ya en el nivel SL 1 —el más básico— se incluye el requisito **SR 6.1: "Audit log capacity"**: los sistemas de control deben tener capacidad para registrar eventos de seguridad y operación.

Este requisito normativo otorga una justificación adicional al proyecto: la monitorización continua de la infraestructura OT no es únicamente una necesidad operativa de GEA, sino un requisito de cumplimiento normativo en el marco de IEC 62443. Las organizaciones que operan infraestructuras críticas —como instalaciones farmacéuticas o de procesado de alimentos sujetas a regulaciones FDA/EFSA— tienen obligaciones específicas de trazabilidad y monitorización de sus sistemas de control.

### Diferencias fundamentales entre IT y OT con implicaciones de diseño

Lee y Kim (2019) [19] sistematizan las diferencias entre IT y OT con implicaciones directas para el diseño de soluciones de monitorización:

| Dimensión | IT | OT | Implicación de diseño |
|---|---|---|---|
| Prioridad de seguridad | CIA (Confidencialidad > Integridad > Disponibilidad) | AIC (Disponibilidad > Integridad > Confidencialidad) | El sistema debe ser no intrusivo y no comprometer la disponibilidad |
| Ciclo de vida de equipos | 3–5 años | 15–30 años | Soporte de protocolos legacy (S7-300, SNMPv2c) |
| Tolerancia a latencia | Alta | Baja (tiempo real crítico) | Polling no debe saturar la red OT |
| Actualizaciones | Frecuentes y automáticas | Excepcionales, con ventanas de mantenimiento | El sistema de monitorización no debe requerir actualizaciones en los equipos monitorizados |
| Conectividad externa | Habitual | Restringida o inexistente | Despliegue autónomo sin dependencias de Internet |

Estas diferencias explican por qué las soluciones IT existentes no pueden simplemente trasladarse al mundo OT, y justifican el diseño específico de agentes de monitorización no intrusivos basados en protocolos de solo lectura.

---

## 2.5 Soluciones comerciales de monitorización y visibilidad OT

En los últimos años ha surgido un mercado específico de plataformas de visibilidad y seguridad OT, impulsado por el crecimiento de los ciberataques a infraestructuras industriales (notablemente el ataque a Colonial Pipeline en 2021 [20] y al sistema de agua de Oldsmar, Florida, en 2021 [21]).

### Plataformas de seguridad OT (enfoque pasivo)

**Claroty** [22] y **Nozomi Networks** [23] son los líderes del mercado de visibilidad OT. Su enfoque principal es el análisis pasivo del tráfico de red mediante un puerto SPAN (mirroring de tráfico de red) o una sonda TAP, lo que permite descubrir activos y detectar anomalías de comportamiento sin interactuar directamente con los dispositivos. Este enfoque tiene la ventaja de ser completamente no intrusivo, pero proporciona una visibilidad limitada de métricas de salud de los propios dispositivos: sabe que un PLC existe en la red y que se comunica de cierta forma, pero no conoce su porcentaje de uso de memoria o si su CPU está en estado RUN o STOP.

**Dragos** [24] está orientado específicamente a la detección de amenazas avanzadas (APT) en infraestructuras industriales críticas (energía, petróleo, agua), con un enfoque de threat intelligence y respuesta a incidentes más que de monitorización operativa.

El coste de estas plataformas —generalmente entre 30.000 y 200.000 euros anuales según el tamaño de la instalación— las hace inaccesibles para organizaciones de tamaño medio y proyectos académicos, y justifica el desarrollo de una alternativa open source.

### Historians de proceso (enfoque en datos de producción)

**AVEVA PI System** (anteriormente OSIsoft PI) [25] es el *historian* industrial de referencia: un sistema de almacenamiento y análisis de datos de proceso (temperaturas, presiones, caudales) con décadas de historia y una penetración muy amplia en industria pesada, energía y farmacéutica. Sin embargo, PI System está orientado a *datos de proceso* (variables del proceso productivo) y no a *métricas de infraestructura* (salud de los servidores o PLCs como dispositivos computacionales). Su integración con protocolos modernos (OPC UA, REST) ha mejorado en las últimas versiones, pero su arquitectura propietaria y su modelo de licencias por punto de datos siguen siendo barreras significativas.

**InfluxDB + Grafana** como alternativa open source ha ganado adopción creciente en entornos industriales medianos [26], precisamente por la combinación de rendimiento, flexibilidad y coste cero de licencias. Esta es la elección tecnológica del presente proyecto.

---

## 2.6 Bases de datos de series temporales

Los datos de monitorización tienen una naturaleza inherentemente temporal: cada métrica es un par (timestamp, valor) asociado a un origen. El patrón de acceso es casi exclusivamente por rango temporal (*dame los valores de CPU de los últimos 24 horas*) y de agregación (*la media de RAM de todos los servidores en el último minuto*). Este patrón es radicalmente diferente al de las bases de datos relacionales, optimizadas para accesos por clave primaria y joins complejos.

### Limitaciones de las BBDD relacionales para series temporales

El almacenamiento de métricas en bases de datos relacionales (MySQL, PostgreSQL) es técnicamente posible —Zabbix lo hace— pero presenta problemas de escalabilidad: las tablas de métricas crecen indefinidamente, los índices se vuelven enormes, y las consultas por rango temporal de millones de filas son lentas. Además, el modelo relacional no tiene primitivas para operaciones comunes en series temporales como la interpolación, el downsampling o la agregación por ventanas temporales. Mazumdar et al. (2019) [27] demuestran que InfluxDB supera a PostgreSQL en un factor de 3-10x en velocidad de inserción y de 5-20x en velocidad de consulta para cargas de trabajo típicas de monitorización.

### InfluxDB 2.x y el lenguaje Flux

**InfluxDB 2.x** [28] introduce cambios significativos respecto a la versión 1.x: unifica en un solo proceso el servidor de almacenamiento, la interfaz web de administración y el motor de alertas (Tasks); y adopta el lenguaje de consultas **Flux**, un lenguaje funcional que trata las series temporales como tablas y permite transformaciones complejas mediante encadenamiento de funciones. El operador `pivot()` de Flux es especialmente relevante para este proyecto: transforma el formato columnar nativo de InfluxDB en un formato fila-por-activo adecuado para respuestas de API REST, simplificando la integración con plataformas externas como Codex.

El modelo de datos se basa en tres conceptos: **measurement** (agrupa métricas del mismo tipo), **tags** (dimensiones de baja cardinalidad, indexadas) y **fields** (valores numéricos o string, no indexados). Los tags deben tener baja cardinalidad (identificadores de activo), mientras que los fields son los valores que varían continuamente (CPU al 45.3%).

En abril de 2025 InfluxData publicó como GA **InfluxDB 3.0 Core** [28a], una reescritura completa en Rust que reemplaza Flux por SQL nativo y usa almacenamiento columnar (Apache Parquet), eliminando las limitaciones de cardinalidad del motor TSM anterior. Sin embargo, la versión 3.0 Core está diseñada como *edge collector* con límite de 5 bases de datos, y benchmarks independientes muestran que su velocidad de ingesta es inferior a la de la v2.7 para conjuntos de datos de menos de un millón de dispositivos [28b]. Por este motivo, el presente proyecto utiliza **InfluxDB 2.7**, que representa la versión de producción más estable y madura, con integración nativa en Grafana y soporte completo de Flux.

### Comparativa de alternativas

| Base de datos | Ventajas | Limitaciones para este proyecto |
|---|---|---|
| **InfluxDB 2.7** | Flux, integración Grafana nativa, Docker, producción estable | — (elección principal) |
| **InfluxDB 3.0** | SQL nativo, sin límite de cardinalidad, Rust | Límite 5 DBs en Core, menor velocidad de ingesta en datasets pequeños |
| **TimescaleDB** | SQL estándar, extensión PostgreSQL | Requiere PostgreSQL, mayor complejidad operativa |
| **Prometheus** | Pull-based, alertas nativas, CNCF | No diseñado para retención larga, modelo push complejo |
| **Victoria Metrics** | Muy eficiente, compatible PromQL | Menor integración con Grafana para Flux |
| **ClickHouse** | Excelente analítica, muy rápido | No optimizado para escritura de alta frecuencia puntual |

---

## 2.7 Arquitectura de microservicios y contenedorización en entornos industriales

### El patrón de agente recolector

Burns, Grant y Oppenheimer (2016) [29] en su trabajo seminal sobre diseño de sistemas distribuidos basados en contenedores identifican el patrón **sidecar**: un proceso ligero que acompaña a un sistema principal, recolectando sus métricas y enviándolas a un almacén centralizado. Este patrón es la referencia arquitectural para los agentes de este proyecto: cada agente es un contenedor independiente que implementa la lógica de recolección para un tipo de protocolo, escribe en InfluxDB, y puede actualizarse o escalarse de forma independiente del resto del sistema.

La separación de responsabilidades por agente tiene ventajas prácticas en un entorno OT: si el agente Siemens falla (por ejemplo, por un error en la comunicación con un PLC específico), el agente de servidores y el agente VMware siguen funcionando sin interrupción. Esta resiliencia por aislamiento es uno de los requisitos clave del diseño.

### Docker Compose como orquestador ligero para entornos industriales

Kubernetes [30] es el estándar de orquestación de contenedores en entornos cloud-native, pero su complejidad operativa lo hace inadecuado para despliegues en sitio (*on-premise*) en plantas industriales donde el personal de IT puede ser limitado y la infraestructura de servidores es modesta. **Docker Compose** [31] proporciona una alternativa declarativa y simple: un único fichero YAML define todos los servicios del stack, sus dependencias, volúmenes persistentes y variables de entorno. El stack completo (InfluxDB, Grafana, agentes, API) se levanta con un único comando, garantizando reproducibilidad en cualquier host con Docker instalado.

Esta característica es especialmente valiosa en entornos industriales donde se requiere poder replicar el sistema en una nueva planta con mínima fricción operativa.

### APIs REST para integración de datos industriales

El modelo REST (Representational State Transfer, Fielding 2000) [32] se ha convertido en el estándar de facto para la integración de sistemas heterogéneos. En el contexto industrial, la IEC 62541-6 [33] (OPC UA Information Model for REST) y las iniciativas de **NAMUR Open Architecture** (NOA) promueven explícitamente el uso de APIs REST como capa de integración entre los sistemas de control OT y las plataformas corporativas IT.

El framework **FastAPI** [34] (Python) permite desarrollar APIs REST de alto rendimiento con documentación automática Swagger/OpenAPI, validación de datos mediante Pydantic, y soporte asíncrono nativo. Su elección para este proyecto está respaldada por estudios comparativos que lo posicionan como el framework Python más rápido para APIs REST, comparable en rendimiento a frameworks Node.js y Go para cargas de trabajo de I/O-bound [35].

---

## 2.8 Conclusiones de la investigación previa

El análisis del estado del arte en las áreas relevantes para este proyecto permite extraer las siguientes conclusiones que fundamentan las decisiones de diseño:

**Sobre herramientas de monitorización existentes:** Las herramientas IT open source han avanzado hacia el mundo OT: Zabbix 7.x incluye soporte nativo de Modbus TCP/RTU y se posiciona explícitamente como solución *IT & OT*, mientras que PRTG (comercial) dispone de sensores nativos para OPC UA, Modbus y EtherNet/IP. Sin embargo, ninguna de estas herramientas cubre de forma nativa los protocolos específicamente necesarios para este proyecto: **OPC UA** como cliente activo hacia el servidor nativo del S7-1500, ni **S7Comm** (protocolo Snap7) para la gama S7 completa incluyendo modelos legacy (S7-300, S7-400). Adicionalmente, el modelo de licencias de PRTG (por sensor) lo hace inviable a escala industrial, y la configuración dinámica de targets (alta/baja sin reinicio) no es un patrón soportado de forma nativa en ninguna de estas plataformas. Las plataformas comerciales OT (Claroty, Nozomi) están orientadas a seguridad pasiva, no a observabilidad operativa de infraestructura, y su coste es prohibitivo. Esta brecha justifica el desarrollo de una solución específica basada en agentes Python con librerías de protocolo dedicadas.

**Sobre protocolos:** La combinación OPC UA (estándar abierto, soportado por Siemens S7-1500 nativamente) + Snap7 (compatibilidad con toda la gama S7, incluyendo modelos legacy) proporciona la cobertura de protocolos más amplia para el entorno Siemens de GEA. SNMP + WinRM cubre los servidores Windows sin necesidad de instalar agentes propietarios.

**Sobre almacenamiento:** InfluxDB 2.x es la opción óptima para el patrón de datos del proyecto (alta frecuencia de escritura, consultas por rango temporal, integración con Grafana), con ventaja demostrada frente a alternativas relacionales y mayor madurez que competidores como Victoria Metrics.

**Sobre arquitectura:** El patrón de agentes independientes por protocolo, contenedorizados con Docker Compose, proporciona la modularidad y resiliencia requeridas en un entorno industrial, con una complejidad operativa adecuada para un despliegue *on-premise*.

**Sobre configuración dinámica:** La integración con la plataforma Codex de GEA requiere una API REST con capacidad de gestión dinámica de targets (POST/DELETE sin reinicio de agentes), un patrón bien establecido en sistemas distribuidos mediante el uso de un poller que detecta cambios de configuración y ajusta el scheduling en tiempo de ejecución.

---

**Referencias bibliográficas:**

[1] Galstad, E. (2009). *Nagios: System and Network Monitoring* (2nd ed.). No Starch Press.

[2] Icinga Project. (2024). *Icinga Documentation*. https://icinga.com/docs/

[3] Zabbix LLC. (2024). *Zabbix Documentation 7.2*. https://www.zabbix.com/documentation/7.2/

[3a] Zabbix LLC. (2024). *Zabbix — The universal, open-source observability solution for IT & OT*. https://www.zabbix.com/

[4] Paessler AG. (2024). *PRTG Network Monitor Manual*. https://www.paessler.com/manuals/prtg

[4a] Paessler AG. (2025). *PRTG Multi-Platform Probe for Siemens Industrial Edge*. Paessler AG Press Release. https://www.paessler.com/company/press/releases/

[5] Volz, B., & Watts, R. (2018). *Prometheus: Up & Running*. O'Reilly Media.

[6] Grafana Labs. (2024). *Grafana Documentation*. https://grafana.com/docs/

[7] Inductive Automation. (2024). *Ignition Documentation*. https://docs.inductiveautomation.com/

[8] Siemens AG. (2023). *SIMATIC WinCC V7.5 System Manual*. Siemens AG.

[9] ABB Ltd. (2022). *System 800xA Operations Manual*. ABB Ltd.

[10] OPC Foundation. (2017). *OPC Unified Architecture Specification Part 1: Overview and Concepts (IEC 62541-1)*. OPC Foundation. https://reference.opcfoundation.org/

[11] asyncua contributors. (2024). *asyncua: Python OPC-UA client and server library*. https://github.com/FreeOpcUa/opcua-asyncio

[12] Nardella, D. (2023). *Snap7 — A free, open source, multi-platform Siemens S7 Communication library*. http://snap7.sourceforge.net/

[13] Case, J., Fedor, M., Schoffstall, M., & Davin, J. (1990). *RFC 1157: A Simple Network Management Protocol (SNMP)*. IETF. https://datatracker.ietf.org/doc/html/rfc1157

[14] Waldbusser, S. (2000). *RFC 2790: Host Resources MIB*. IETF. https://datatracker.ietf.org/doc/html/rfc2790

[15] DMTF. (2013). *DSP0226: Web Services Management (WS-Management) Specification v1.1.0*. DMTF. https://www.dmtf.org/dsp/DSP0226

[16] pywinrm contributors. (2024). *pywinrm: Python client for Windows Remote Management*. https://github.com/diyan/pywinrm

[17] ISA. (2010). *ANSI/ISA-95.00.01-2010: Enterprise-Control System Integration Part 1: Models and Terminology*. ISA.

[18] IEC. (2018). *IEC 62443-3-3: Industrial communication networks – Network and system security – Part 3-3: System security requirements and security levels*. International Electrotechnical Commission.

[19] Lee, J., & Kim, B. (2019). Challenges and opportunities in cyber-physical systems for manufacturing. *CIRP Annals, 68*(2), 791–814. https://doi.org/10.1016/j.cirp.2019.05.003

[20] CISA. (2021). *Alert (AA21-131A): DarkSide Ransomware: Best Practices for Preventing Business Disruption from Ransomware Attacks*. CISA. https://www.cisa.gov/uscert/ncas/alerts/aa21-131a

[21] Bajak, F. (2021). Florida water treatment plant hack exposes danger lurking in aging, Internet-connected systems. *AP News*, 9 February 2021.

[22] Claroty. (2024). *The Claroty Platform: Comprehensive OT/IoT Security*. https://claroty.com/

[23] Nozomi Networks. (2024). *Nozomi Networks Guardian: OT/IoT Security and Visibility*. https://www.nozominetworks.com/

[24] Dragos. (2023). *ICS/OT Cybersecurity Year in Review 2023*. Dragos Inc. https://www.dragos.com/year-in-review/

[25] AVEVA. (2024). *AVEVA PI System: Industrial Data Management*. https://www.aveva.com/en/products/aveva-pi-system/

[26] Cherki, B., Chiky, R., & Hébrail, G. (2020). Monitoring industrial IoT devices with open-source tools: A comparative study. *IEEE International Conference on Industrial Technology (ICIT)*. https://doi.org/10.1109/ICIT45562.2020.9067256

[27] Mazumdar, S., Dutta, D., Bhatt, D., & Jha, S. (2019). Evaluating time-series databases for IoT monitoring applications. *IEEE International Conference on Big Data*. https://doi.org/10.1109/BigData47090.2019.9006512

[28] InfluxData. (2024). *InfluxDB 2.7 Documentation*. https://docs.influxdata.com/influxdb/v2/

[28a] InfluxData. (2025). *InfluxDB 3.0 Core — Generally Available*. https://docs.influxdata.com/influxdb/v3/

[28b] QuestDB. (2024). *InfluxDB benchmark: write throughput comparison across versions and alternatives*. QuestDB Engineering Blog. https://questdb.io/blog/

[29] Burns, B., Grant, B., Oppenheimer, D., Brewer, E., & Wilkes, J. (2016). Borg, Omega, and Kubernetes. *ACM Queue, 14*(1), 70–93. https://doi.org/10.1145/2898442.2898444

[30] Burns, B., Beda, J., & Hightower, K. (2022). *Kubernetes: Up and Running* (3rd ed.). O'Reilly Media.

[31] Docker Inc. (2024). *Docker Compose Documentation*. https://docs.docker.com/compose/

[32] Fielding, R. T. (2000). *Architectural Styles and the Design of Network-based Software Architectures* (Doctoral dissertation, University of California, Irvine). https://ics.uci.edu/~fielding/pubs/dissertation/top.htm

[33] OPC Foundation. (2020). *OPC UA Part 6: Mappings (HTTP/REST)*. OPC Foundation.

[34] Ramírez, S. (2024). *FastAPI Documentation*. https://fastapi.tiangolo.com/

[35] TechEmpower. (2024). *TechEmpower Framework Benchmarks — Round 22*. https://www.techempower.com/benchmarks/

---

---

# 3. PLAN DE DESARROLLO DEL PROYECTO

## 3.1. Metodología y planificación

### Metodología de desarrollo

El proyecto se desarrolla siguiendo una **metodología iterativa e incremental**, organizada en fases funcionales independientes. Cada fase produce un incremento del sistema completamente funcional, verificable en el entorno real de GEA, y sobre el que se construye la fase siguiente. Esta aproximación es especialmente adecuada para proyectos de ingeniería de software en entornos industriales, por varias razones:

En primer lugar, el acceso a los equipos reales (PLCs, servidores, ESXi) está sujeto a ventanas de disponibilidad operativa, lo que hace inviable un modelo de desarrollo en cascada donde el diseño completo debe estar terminado antes de la implementación. El modelo iterativo permite obtener retroalimentación temprana del sistema real.

En segundo lugar, los requisitos de monitorización de un entorno OT industrial solo se conocen completamente una vez que se interactúa con los equipos reales: los OIDs SNMP disponibles, los nodos OPC UA expuestos por el PLC, o las métricas accesibles vía vSphere solo pueden determinarse con precisión conectándose a los propios dispositivos.

En tercer lugar, la arquitectura modular por agentes se presta naturalmente a un desarrollo iterativo: cada fase añade un nuevo agente al sistema sin modificar los existentes, lo que reduce el riesgo de regresiones.

Las herramientas de gestión del proyecto son las siguientes: **Git** para control de versiones (repositorio GitHub con commits siguiendo la convención *Conventional Commits*: feat, fix, docs, refactor); **Claude Code** (Anthropic) como asistente de programación con IA para generación y revisión de código; y **Codex** (OpenAI), integrado en el flujo de desarrollo como auditor automático de código que analiza cada cambio antes de que la sesión de programación termine.

### Fases del proyecto

| Fase | Nombre | Descripción | Estado |
|------|--------|-------------|--------|
| 0 | Preparación | Análisis de requisitos, estudio de protocolos, diseño de arquitectura, scaffold del proyecto | Completada |
| 1 | Agente de servidores y VMs | SNMP + WinRM + pyVmomi, InfluxDB, Grafana, API REST | Completada |
| 2 | Agente Siemens PLC | OPC UA + Snap7, configuración dinámica (SQLite + ConfigPoller), integración Codex | Completada |
| 3 | Agente Rockwell *(trabajo futuro)* | pylogix / EtherNet/IP | — |
| 4 | Agente de red *(trabajo futuro)* | SNMP + PROFINET DCP | — |
| 5 | Alertas y reporting *(trabajo futuro)* | Grafana Alerting, PDF, email/Teams | — |

Para este PFG se desarrollan completamente las **Fases 0, 1 y 2**. Las Fases 3, 4 y 5 quedan diseñadas arquitectónicamente como trabajo futuro.

### Planificación temporal — Diagrama de Gantt

A continuación se detalla la planificación temporal del proyecto con las tareas, duraciones estimadas y dependencias. [COMPLETAR: construye el diagrama de Gantt visual en Word/Excel a partir de esta tabla, indicando las fechas reales de inicio y fin de cada tarea.]

| ID | Tarea | Duración | Dependencias |
|----|-------|----------|--------------|
| T01 | Análisis de requisitos con GEA y estudio del entorno | 1 semana | — |
| T02 | Estudio de protocolos industriales (SNMP, OPC UA, S7Comm, WinRM) | 2 semanas | T01 |
| T03 | Diseño de arquitectura del sistema (agentes, API, almacenamiento) | 1 semana | T02 |
| T04 | Scaffold del proyecto (Docker Compose, InfluxDB, Grafana, CI/CD) | 1 semana | T03 |
| T05 | Implementación librería compartida (shared/: InfluxWriter, modelos, settings) | 1 semana | T04 |
| T06 | Implementación agente SNMP para servidores Windows | 2 semanas | T05 |
| T07 | Implementación agente WinRM + PowerShell | 1 semana | T05 |
| T08 | Implementación agente VMware ESXi/VMs (pyVmomi) | 2 semanas | T05 |
| T09 | Implementación API REST básica (/metrics/servers, /metrics/vmware) | 1 semana | T06, T07, T08 |
| T10 | Dashboard Grafana Fase 1 (servidores + VMware) | 1 semana | T09 |
| T11 | Pruebas Fase 1 en entorno real GEA (servidores Windows, ESXi) | 1 semana | T10 |
| T12 | Diseño y implementación config dinámica (SQLite + ConfigPoller + /config/targets) | 2 semanas | T11 |
| T13 | Implementación colector OPC UA (Siemens, modo principal) | 2 semanas | T12 |
| T14 | Implementación colector Snap7 (Siemens, modo fallback, SZL reads) | 1 semana | T13 |
| T15 | Integración modo "auto" (OPC UA → Snap7) y scripts de discovery | 1 semana | T13, T14 |
| T16 | Dashboard Grafana Fase 2 (PLCs Siemens) + integración API Codex | 1 semana | T15 |
| T17 | Pruebas Fase 2 en entorno real GEA (PLCs Siemens) | 1 semana | T16 |
| T18 | Redacción de la memoria del proyecto | 3 semanas | T17 |
| T19 | Revisión con tutor y correcciones | 1 semana | T18 |
| T20 | Preparación de la presentación | 1 semana | T19 |

**Duración total estimada: 26 semanas** (~6 meses y medio)

**Período de desarrollo:** [COMPLETAR: mes y año de inicio] — [COMPLETAR: mes y año de fin previsto]

---

## 3.2. Herramientas y recursos

### Lenguajes y frameworks de desarrollo

**Python 3.12** es el lenguaje principal para todos los agentes y la API. La elección se justifica por su ecosistema de librerías industriales —las únicas implementaciones open source maduras de OPC UA, S7Comm, vSphere y WinRM para uso programático son librerías Python— y por su legibilidad y facilidad de mantenimiento, relevantes en un entorno industrial donde el código puede ser mantenido por personal con perfiles técnicos variados.

**FastAPI** (Ramírez, 2018) es el framework web Python utilizado para la API REST. Genera documentación Swagger/OpenAPI de forma automática a partir de las anotaciones de tipo, lo que facilita la integración con Codex sin necesidad de documentación manual adicional. Su rendimiento, demostrado en benchmarks independientes [35], es comparable a frameworks asíncronos de Node.js y Go para cargas de I/O-bound.

**SQLModel** es el ORM utilizado para el almacén de configuración en SQLite. Combina SQLAlchemy (motor de base de datos relacional) y Pydantic (validación de datos) en una única librería, lo que elimina la duplicación de definiciones de esquema habitual en proyectos FastAPI + SQLAlchemy.

### Infraestructura de despliegue

**Docker Desktop** (Windows) y **Docker Compose** son las herramientas de contenedorización y orquestación del stack completo. El entorno de desarrollo local en Windows y el entorno de producción en GEA utilizan el mismo fichero `docker-compose.yml`, garantizando la reproducibilidad del despliegue.

**InfluxDB 2.7** (InfluxData) es la base de datos de series temporales para el almacenamiento de todas las métricas de monitorización. Se despliega como contenedor Docker con volúmenes persistentes para los datos y la configuración.

**Grafana 10.4** (Grafana Labs) es la plataforma de visualización. Los dashboards se provisionan automáticamente desde ficheros JSON al arrancar el contenedor, eliminando la necesidad de configuración manual en cada despliegue.

### Librerías Python principales

| Librería | Versión | Propósito |
|---|---|---|
| `asyncua` | 1.0.6 | Cliente OPC UA asíncrono (Python 3.12 compatible) |
| `python-snap7` | 1.3 | Wrapper Python para librería nativa Snap7 (S7Comm) |
| `pyVmomi` | 8.0.2.0 | SDK oficial Python para VMware vSphere API |
| `pysnmp-lextudio` | 6.1.3 | Fork de pysnmp compatible con Python 3.12 |
| `pywinrm` | 0.4.3 | Cliente WinRM para PowerShell remoto |
| `APScheduler` | 3.10.4 | Scheduler de tareas periódicas con soporte dinámico de jobs |
| `influxdb-client` | 1.44.0 | Cliente oficial Python para InfluxDB 2.x |
| `pydantic-settings` | 2.2.1 | Gestión de configuración mediante variables de entorno |

### Herramientas de control de calidad y desarrollo

**Git** y **GitHub** para control de versiones, con el repositorio alojado en [COMPLETAR: URL del repositorio].

**Claude Code** (Anthropic, 2024) es el asistente de programación con IA utilizado a lo largo del proyecto para la generación de código, revisión de arquitectura y resolución de problemas técnicos. Su integración en el entorno de desarrollo (VS Code y terminal) permite mantener el contexto del proyecto entre sesiones mediante un sistema de memoria persistente.

**Codex** (OpenAI, 2024), integrado como plugin en Claude Code, actúa como **auditor automático de código**: analiza cada cambio realizado en el código antes de que la sesión de desarrollo termine, identificando posibles problemas de seguridad, race conditions, y desviaciones de las buenas prácticas. Este flujo de revisión continua garantiza una calidad de código consistente a lo largo del proyecto.

**VS Code** con las extensiones Python (Pylance, Black Formatter), Docker, y REST Client como entorno de desarrollo integrado.

### Recursos de la empresa GEA Process Engineering

El proyecto se desarrolla en colaboración con GEA Process Engineering, que proporciona los siguientes recursos:

**Infraestructura de pruebas en entorno real.** GEA facilita el acceso a servidores Windows con SNMP habilitado, hipervisores VMware ESXi con máquinas virtuales de producción, y PLCs Siemens de la familia S7 en funcionamiento real en planta. [COMPLETAR: si puedes mencionar el número aproximado de equipos o el tipo de entorno (laboratorio, planta piloto, etc.) sin comprometer información confidencial.]

**Acceso a la plataforma Codex.** GEA proporciona acceso a la API de su plataforma interna Codex para probar la integración de registro dinámico de targets y la consulta de métricas desde Codex hacia el sistema desarrollado.

**Conocimiento de dominio industrial.** El personal técnico de GEA ha proporcionado información sobre la arquitectura de red de las instalaciones, los modelos específicos de PLC utilizados, los protocolos habilitados en cada equipo, y los requisitos operativos que debe cumplir el sistema de monitorización (no intrusividad, no modificación de configuraciones, compatibilidad con ventanas de mantenimiento).

**Infraestructura de red.** El acceso a la red OT de GEA para las pruebas de conectividad y validación del sistema se realiza bajo supervisión del equipo técnico, respetando en todo momento las políticas de seguridad de la empresa.

### Recursos académicos

- Biblioteca de la Universidad Francisco de Vitoria: acceso a IEEE Xplore, ACM Digital Library y SpringerLink para la consulta de artículos académicos y estándares técnicos.
- [COMPLETAR: añade si has consultado recursos académicos adicionales, como MOOCs, libros específicos, o tutoriales técnicos especializados.]

---
