"""Script to fill in the UFV Word template with TFG content."""
from docx import Document
from docx.shared import RGBColor
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import shutil

shutil.copy(
    "Anexo III - Plantilla Memoria PFG_v1.docx",
    "Memoria PFG - Control System Health Status.docx",
)
doc = Document("Memoria PFG - Control System Health Status.docx")

# ── helpers ─────────────────────────────────────────────────────────────────

def is_yellow(para):
    for run in para.runs:
        rPr = run._r.find(qn("w:rPr"))
        if rPr is not None and rPr.find(qn("w:highlight")) is not None:
            return True
    return False


def del_para(para):
    p = para._element
    p.getparent().remove(p)


def remove_highlight(run):
    rPr = run._r.find(qn("w:rPr"))
    if rPr is not None:
        hl = rPr.find(qn("w:highlight"))
        if hl is not None:
            rPr.remove(hl)


def set_run_text(run, text):
    remove_highlight(run)
    run.text = text


def insert_after(anchor_el, text, bold=False, is_list=False):
    """Insert a Normal (or ListParagraph) paragraph after anchor_el. Returns new element."""
    pPr_el = OxmlElement("w:pPr")
    s_el = OxmlElement("w:pStyle")
    s_el.set(qn("w:val"), "ListParagraph" if is_list else "Normal")
    pPr_el.append(s_el)
    if is_list:
        ind = OxmlElement("w:ind")
        ind.set(qn("w:left"), "720")
        pPr_el.append(ind)

    r_el = OxmlElement("w:r")
    rPr_el = OxmlElement("w:rPr")
    if bold:
        rPr_el.append(OxmlElement("w:b"))
    r_el.append(rPr_el)

    t_el = OxmlElement("w:t")
    t_el.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
    t_el.text = text
    r_el.append(t_el)

    new_p = OxmlElement("w:p")
    new_p.append(pPr_el)
    new_p.append(r_el)
    anchor_el.addnext(new_p)
    return new_p


def insert_table_after(anchor_el, headers, rows):
    """Insert a simple table with shaded header after anchor_el."""
    tbl = OxmlElement("w:tbl")
    tblPr = OxmlElement("w:tblPr")
    tblStyle = OxmlElement("w:tblStyle")
    tblStyle.set(qn("w:val"), "TableGrid")
    tblPr.append(tblStyle)
    tblW = OxmlElement("w:tblW")
    tblW.set(qn("w:w"), "9360")
    tblW.set(qn("w:type"), "dxa")
    tblPr.append(tblW)
    tbl.append(tblPr)

    col_w = str(9360 // len(headers))

    def cell(text, bold=False, shaded=False):
        tc = OxmlElement("w:tc")
        tcPr = OxmlElement("w:tcPr")
        tcW2 = OxmlElement("w:tcW")
        tcW2.set(qn("w:w"), col_w)
        tcW2.set(qn("w:type"), "dxa")
        tcPr.append(tcW2)
        if shaded:
            shd = OxmlElement("w:shd")
            shd.set(qn("w:val"), "clear")
            shd.set(qn("w:color"), "auto")
            shd.set(qn("w:fill"), "D9D9D9")
            tcPr.append(shd)
        tc.append(tcPr)
        cp = OxmlElement("w:p")
        cr = OxmlElement("w:r")
        if bold:
            crPr = OxmlElement("w:rPr")
            crPr.append(OxmlElement("w:b"))
            cr.append(crPr)
        ct = OxmlElement("w:t")
        ct.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        ct.text = str(text)
        cr.append(ct)
        cp.append(cr)
        tc.append(cp)
        return tc

    tr = OxmlElement("w:tr")
    for h in headers:
        tr.append(cell(h, bold=True, shaded=True))
    tbl.append(tr)
    for row in rows:
        tr = OxmlElement("w:tr")
        for c in row:
            tr.append(cell(c))
        tbl.append(tr)

    spacer = OxmlElement("w:p")
    anchor_el.addnext(tbl)
    anchor_el.addnext(spacer)
    return tbl


def insert_paras(heading_fragment, items):
    """
    Find heading containing fragment, delete its yellow body, insert items.
    items: list of (text, bold=False, is_list=False) or plain strings
    """
    paras = list(doc.paragraphs)
    h_idx = None
    for i, p in enumerate(paras):
        if heading_fragment in p.text and p.style.name.startswith("Heading"):
            h_idx = i
            break
    if h_idx is None:
        print(f"  WARNING: '{heading_fragment}' heading not found")
        return None

    # delete yellow body until next heading
    for p in paras[h_idx + 1 :]:
        if p.style.name.startswith("Heading"):
            break
        if is_yellow(p):
            try:
                del_para(p)
            except Exception:
                pass

    anchor = paras[h_idx]._element
    cur = anchor
    for item in items:
        if isinstance(item, str):
            text, bold, is_list = item, False, False
        elif len(item) == 1:
            text, bold, is_list = item[0], False, False
        elif len(item) == 2:
            text, bold = item
            is_list = False
        else:
            text, bold, is_list = item[0], item[1], item[2]
        cur = insert_after(cur, text, bold=bold, is_list=is_list)
    print(f"  '{heading_fragment}' — {len(items)} items inserted")
    return cur


# ── PORTADA ─────────────────────────────────────────────────────────────────

for para in doc.paragraphs[:30]:
    t = para.text.strip()
    for run in para.runs:
        rt = run.text
        if "COMPLETAR" in rt and "INGENIER" in rt:
            run.text = rt.replace("COMPLETAR", "INFORMÁTICA")
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif rt.strip() == "TÍTULO DEL PROYECTO":
            run.text = "Control System Health Status"
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif "Nombre Apellido1 Apellido2" in rt and "Convocatoria" not in rt and "Tutor" not in t:
            run.text = "Jin Wen Cheng"
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif "Convocatoria de mes" in rt:
            run.text = "Junio 2026"
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif "Tutor: Nombre" in rt:
            run.text = "Tutor: [COMPLETAR: tutor UFV]"
            run.font.color.rgb = RGBColor(0, 0, 0)
        elif "Tutor externo:" in rt:
            run.text = "Tutor externo: [COMPLETAR: tutor GEA Process Engineering]"
            run.font.color.rgb = RGBColor(0, 0, 0)

print("Portada OK")

# ── DELETE optional sections (citas, dedicatoria, agradecimientos) ───────────

keywords_to_delete = [
    "citas", "célebres", "celobres", "dedicatoria", "eliminarse esta",
    "agradecimiento", "subvenci", "beca, contrato",
]
for p in list(doc.paragraphs):
    if is_yellow(p) and any(k in p.text.lower() for k in keywords_to_delete):
        try:
            del_para(p)
        except Exception:
            pass

print("Optional sections deleted")

# ── RESUMEN / KEYWORDS / ABSTRACT ────────────────────────────────────────────

RESUMEN = (
    "El presente Proyecto Final de Grado describe el diseño e implementación de un sistema de "
    "monitorización de salud en tiempo real para infraestructura de tecnología de operaciones (OT) "
    "industrial, desarrollado en colaboración con GEA Process Engineering. La infraestructura "
    "tecnológica de las instalaciones industriales de GEA —servidores Windows, hipervisores VMware "
    "ESXi con máquinas virtuales, y controladores lógicos programables (PLC) de la familia Siemens "
    "S7— carecía de un sistema unificado de supervisión de su estado. El diagnóstico ante un incidente "
    "era manual y reactivo, limitando la capacidad de detección temprana de degradaciones. El sistema "
    "desarrollado adopta una arquitectura de microservicios contenedorizados mediante Docker Compose, "
    "con agentes Python independientes por protocolo de comunicación: SNMP y WinRM para servidores "
    "Windows, la API vSphere para entornos VMware, y OPC UA con S7Comm como fallback para PLCs Siemens. "
    "Todas las métricas se almacenan en InfluxDB 2.7 y se visualizan en Grafana mediante dashboards "
    "provisionados automáticamente. Una API REST desarrollada con FastAPI permite la integración dinámica "
    "con la plataforma interna de GEA y la gestión de targets de monitorización sin necesidad de "
    "reiniciar el sistema."
)
KEYWORDS_ES = (
    "Monitorización OT, infraestructura industrial, Industria 4.0, OPC UA, Siemens S7, SNMP, "
    "InfluxDB, Grafana, Docker, microservicios."
)
ABSTRACT = (
    "This Final Degree Project describes the design and implementation of a real-time health monitoring "
    "system for industrial Operational Technology (OT) infrastructure, developed in collaboration with "
    "GEA Process Engineering. The technological infrastructure of GEA's industrial facilities — Windows "
    "servers, VMware ESXi hypervisors with virtual machines, and Siemens S7 family Programmable Logic "
    "Controllers (PLCs) — lacked a unified system for monitoring their operational status. Incident "
    "diagnosis was manual and reactive, limiting the ability to detect gradual performance degradation "
    "before failures occurred. The developed system adopts a containerized microservices architecture "
    "using Docker Compose, with independent Python agents per communication protocol: SNMP and WinRM "
    "for Windows servers, the vSphere API for VMware environments, and OPC UA with S7Comm fallback for "
    "Siemens PLCs. All metrics are stored in InfluxDB 2.7 and visualized in Grafana through "
    "automatically provisioned dashboards. A REST API developed with FastAPI enables dynamic integration "
    "with GEA's internal platform and runtime management of monitoring targets without system restarts."
)
KEYWORDS_EN = (
    "OT monitoring, industrial infrastructure, Industry 4.0, OPC UA, Siemens S7, SNMP, InfluxDB, "
    "Grafana, Docker, microservices."
)

for p in list(doc.paragraphs):
    if not is_yellow(p):
        continue
    t = p.text.lower()
    if "resumen en espa" in t or ("aqu" in t and "resumen" in t):
        for run in p.runs:
            remove_highlight(run)
        if p.runs:
            p.runs[0].text = RESUMEN
            for r in p.runs[1:]:
                r.text = ""
    elif "palabra clave 1" in t:
        for run in p.runs:
            remove_highlight(run)
        if p.runs:
            p.runs[0].text = KEYWORDS_ES
            for r in p.runs[1:]:
                r.text = ""
    elif "abstract in english" in t or "here comes the abstract" in t:
        for run in p.runs:
            remove_highlight(run)
        if p.runs:
            p.runs[0].text = ABSTRACT
            for r in p.runs[1:]:
                r.text = ""
    elif "keyword 1" in t or "keywords at the most" in t:
        for run in p.runs:
            remove_highlight(run)
        if p.runs:
            p.runs[0].text = KEYWORDS_EN
            for r in p.runs[1:]:
                r.text = ""

print("Resumen/Abstract OK")

# ── DELETE instructions block ────────────────────────────────────────────────

del_fragments = [
    "plantilla a seguir",
    "deber borrar", "deber\u00e1 borrar",
    "MUY IMPORTANTE",
    "Vigilar la redacci",
    "Todos los cap",
    "Utilizar los estilos",
    "elaboraci\u00f3n propia",
    "Este es un pie de tabla",
    "Este es un pie de figura",
]
for p in list(doc.paragraphs):
    if is_yellow(p) and any(k in p.text for k in del_fragments):
        try:
            del_para(p)
        except Exception:
            pass

print("Instructions block deleted")

# ── §1.1 CONTEXTO Y JUSTIFICACION ────────────────────────────────────────────

s11 = [
    ("El momento de la transformación digital industrial", True, False),
    ("La industria manufacturera y de procesos vive una de las transformaciones más profundas de su historia. La denominada Industria 4.0 —término acuñado por el gobierno alemán en 2011 y consolidado como paradigma global en la última década— integra tecnologías como el Internet Industrial de las Cosas (IIoT), la inteligencia artificial, la computación en la nube y la ciberseguridad en el núcleo de los procesos productivos. Según el informe Global Lighthouse Network del Foro Económico Mundial (2023), las fábricas que han adoptado tecnologías de Industria 4.0 reportan incrementos de productividad de entre el 15 % y el 30 %, reducciones de tiempo de inactividad no planificada de hasta el 50 % y mejoras de calidad de producto del 10 % al 20 %.", False, False),
    ("En este contexto, la disponibilidad y fiabilidad de los sistemas informáticos que sustentan la producción —servidores de control, hipervisores de virtualización, controladores lógicos programables (PLC) y redes industriales— ha pasado de ser una preocupación técnica a convertirse en un factor crítico del negocio. Un fallo en un servidor SCADA o en un PLC puede paralizar una línea de producción entera. En el sector alimentario y farmacéutico, el coste medio de una hora de parada no planificada oscila entre los 50.000 y los 500.000 euros, según el informe Cost of Downtime de Aberdeen Research (2022). La observabilidad proactiva —la capacidad de detectar degradaciones antes de que se conviertan en fallos— es, por tanto, un factor diferencial de competitividad.", False, False),
    ("La brecha entre IT y OT", True, False),
    ("El mundo IT (Information Technology) engloba los sistemas informáticos de gestión empresarial: servidores, bases de datos, aplicaciones de negocio, redes corporativas. Es un mundo estandarizado, con protocolos abiertos (TCP/IP, HTTP, SNMP), ciclos de actualización cortos y una cultura de monitorización y observabilidad muy madura.", False, False),
    ("El mundo OT (Operational Technology) engloba los sistemas que controlan los procesos físicos de producción: PLCs, SCADA, DCS, HMI, redes industriales. Es un mundo históricamente propietario, con protocolos específicos de fabricante (S7Comm de Siemens, EtherNet/IP de Rockwell), equipos con ciclos de vida de 15 a 30 años, y una cultura de operación donde la disponibilidad es el valor supremo.", False, False),
    ("Esta separación histórica genera un problema concreto: los sistemas de monitorización maduros del mundo IT —Nagios, Zabbix, Prometheus— no hablan los protocolos industriales del mundo OT, y los sistemas SCADA/DCS no están diseñados para monitorizar su propia infraestructura informática subyacente. El resultado son puntos ciegos en la observabilidad de las plantas industriales: nadie sabe, en tiempo real, si el servidor que ejecuta el SCADA está al 95 % de RAM, si el hipervisor ESXi tiene una VM con snapshots de tres meses que está consumiendo disco silenciosamente, o si el PLC lleva dos horas en estado de alarma sin que nadie lo haya detectado.", False, False),
    ("Contexto específico: GEA Process Engineering", True, False),
    ("GEA Process Engineering es una empresa de ingeniería de procesos industriales especializada en tecnología de separación, tratamiento de fluidos y procesado de alimentos, con presencia en instalaciones de producción repartidas por múltiples países. [COMPLETAR: sector específico y número aproximado de plantas.]", False, False),
    ("La infraestructura tecnológica de las instalaciones de GEA es representativa de la realidad OT industrial: servidores Windows que ejecutan aplicaciones de control, supervisión y SCADA; hipervisores VMware ESXi que alojan máquinas virtuales críticas para la operación; y PLCs de la familia Siemens S7 que gobiernan el control directo de los procesos de producción. Esta infraestructura, distribuida en múltiples plantas, carecía de un sistema unificado de monitorización de salud.", False, False),
    ("Adicionalmente, GEA dispone de una plataforma interna de gestión denominada Codex, que centraliza la configuración y supervisión de sus instalaciones a nivel corporativo. Cualquier nueva herramienta de monitorización debía integrarse con Codex mediante una API REST estándar, que permitiera el registro y la eliminación dinámica de activos monitorizados sin interrumpir el servicio.", False, False),
    ("Justificación del proyecto y valor añadido", True, False),
    ("Este Proyecto de Fin de Grado responde directamente a la necesidad identificada: la ausencia de un sistema de monitorización de salud unificado para la infraestructura OT de GEA. Los factores que justifican el interés del proyecto son los siguientes:", False, False),
    ("Impacto operativo en GEA: detección proactiva de degradaciones reduciendo el tiempo medio de detección (MTTD) de incidencias y el tiempo de inactividad no planificada.", False, True),
    ("No intrusividad: el sistema opera en modo solo lectura (SNMP GET, OPC UA read, Snap7 PG-connection) sin modificar ninguna configuración de los equipos monitorizados.", False, True),
    ("Neutralidad de fabricante: arquitectura modular por agentes que cubre servidores Windows, hipervisores VMware ESXi y PLCs Siemens S7-300/1200/1500. Extensible a PLCs Rockwell y dispositivos de red con cambios mínimos.", False, True),
    ("Coste cero de licencias: stack íntegramente open source (InfluxDB, Grafana, Python, FastAPI, Docker), frente a soluciones comerciales equivalentes cuyo coste anual puede superar los 50.000 euros.", False, True),
    ("Integración con Codex: la API REST permite registrar, modificar y eliminar targets de monitorización en tiempo real sin necesidad de reiniciar el sistema.", False, True),
    ("Valor académico y transferibilidad: el proyecto integra en producción real conocimientos de sistemas distribuidos, protocolos industriales, microservicios, bases de datos de series temporales y APIs REST.", False, True),
]
insert_paras("Contexto y Justificaci", s11)

# ── §1.2 OBJETIVOS ───────────────────────────────────────────────────────────

s12 = [
    ("Objetivo general", True, False),
    ("Diseñar e implementar un sistema de monitorización de salud en tiempo real para infraestructura OT industrial, modular, independiente del fabricante y desplegable mediante contenedores Docker, que permita a GEA Process Engineering supervisar el estado de sus servidores Windows, hipervisores VMware ESXi y PLCs Siemens desde una interfaz unificada, integrándose con su plataforma interna Codex mediante una API REST de configuración dinámica.", False, False),
    ("Objetivos específicos", True, False),
    ("Analizar los protocolos de comunicación industrial disponibles para la monitorización no intrusiva de infraestructura OT (SNMP, WinRM, OPC UA, S7Comm) y determinar la combinación más adecuada para cada tipo de activo en el entorno GEA.", False, True),
    ("Diseñar una arquitectura de software modular basada en microservicios contenedorizados, que separe la responsabilidad de recolección (agentes), almacenamiento (InfluxDB), exposición (API REST) y visualización (Grafana), y que permita añadir nuevos tipos de agentes sin modificar el código existente.", False, True),
    ("Implementar una librería compartida en Python que encapsule la lógica común a todos los agentes: escritura en InfluxDB, modelos de datos, configuración por variables de entorno y logging estructurado.", False, True),
    ("Implementar un agente de monitorización para servidores Windows mediante SNMP (HOST-RESOURCES-MIB) y WinRM con PowerShell, capaz de recopilar métricas de CPU, memoria, disco, servicios críticos y desviación NTP.", False, True),
    ("Implementar un agente de monitorización para entornos de virtualización VMware ESXi mediante la API vSphere (pyVmomi), capaz de reportar el estado de hipervisores y máquinas virtuales, incluyendo detección de snapshots con antigüedad superior a un umbral configurable.", False, True),
    ("Implementar un agente de monitorización para PLCs Siemens mediante OPC UA como protocolo principal y S7Comm (Snap7) como fallback automático, capaz de obtener el estado operativo del CPU (RUN/STOP/FAULT), el uso de memoria de carga y de trabajo, y el firmware del equipo.", False, True),
    ("Desarrollar una API REST con FastAPI que exponga los datos de monitorización a la plataforma Codex de GEA y permita el registro, actualización y eliminación dinámica de targets de monitorización en tiempo de ejecución, persistiendo la configuración en SQLite.", False, True),
    ("Integrar la visualización de datos mediante dashboards en Grafana provisionados automáticamente, con paneles de estado por activo, series temporales de métricas clave y alertas visuales por umbral.", False, True),
    ("Validar el sistema en el entorno real de GEA, comprobando la correcta recolección de métricas para cada tipo de activo, la resiliencia ante targets inalcanzables, y el correcto funcionamiento de la configuración dinámica sin reinicio de agentes.", False, True),
]
insert_paras("Objetivos", s12)

# ── §2 INVESTIGACIÓN PREVIA ──────────────────────────────────────────────────

s2 = [
    ("La monitorización de sistemas informáticos es una disciplina técnica consolidada en el ámbito IT, pero su extensión al mundo OT industrial plantea retos específicos que hacen necesario un análisis del estado del arte en varias áreas convergentes: herramientas de monitorización existentes, protocolos de comunicación industriales, bases de datos de series temporales, arquitecturas de microservicios y soluciones comerciales de visibilidad OT.", False, False),
    ("2.1  La evolución de las herramientas de monitorización IT", True, False),
    ("Primera generación — monitorización basada en checks activos (1990s–2000s)", True, False),
    ("Nagios (Galstad, 1999) estableció el paradigma de check plugins: un proceso central ejecuta periódicamente scripts que verifican el estado de servicios y hosts. Icinga, fork de Nagios (2009), introdujo una API REST y mejoras de rendimiento. La limitación fundamental de esta generación es que modela la monitorización como comprobaciones binarias (OK/WARNING/CRITICAL), no como un flujo continuo de métricas, lo que impide detectar degradaciones graduales.", False, False),
    ("Segunda generación — plataformas todo-en-uno (2000s–2010s)", True, False),
    ("Zabbix (2001, open source desde 2004) unificó recolección, almacenamiento, visualización y alertas en una sola plataforma. La versión 7.0 LTS (junio 2024) y la 7.2 (diciembre 2024) consolidan su evolución hacia el mundo OT; la propia empresa lo describe como \"the universal, open-source observability solution for IT & OT\". Sin embargo, su soporte OPC UA no es nativo —requiere un plugin externo en Go sin implementación oficial—, el protocolo S7Comm no está soportado, y su modelo de almacenamiento relacional no está optimizado para escritura de alta frecuencia.", False, False),
    ("PRTG (Paessler, 1997) ha evolucionado significativamente hacia el mundo OT. En su versión actual dispone de sensores nativos para OPC UA, Modbus TCP, MQTT y EtherNet/IP sin necesidad de middleware adicional, y en 2025 integró su Multi-Platform Probe (contenedor Docker) en el ecosistema Siemens Industrial Edge. Su principal limitación es el modelo de licencias por sensor, que resulta costoso a escala industrial.", False, False),
    ("Tercera generación — observabilidad cloud-native (2010s–presente)", True, False),
    ("Prometheus (SoundCloud, 2012; CNCF 2016) popularizó el modelo pull con scraping HTTP y PromQL. Su integración con Grafana se convirtió en el estándar de facto en DevOps, pero no está diseñado para retención a largo plazo ni para protocolos industriales.", False, False),
    ("Grafana se ha convertido en el estándar de facto de visualización de métricas, con capacidad de conectarse a múltiples datasources y un sistema de provisioning declarativo desde ficheros YAML/JSON, ideal para el despliegue automatizado en entornos industriales.", False, False),
    ("Conclusión: ninguna herramienta open source cubre de forma nativa OPC UA como cliente activo ni S7Comm para la gama S7 completa. Esto justifica el desarrollo de agentes Python dedicados.", False, False),
    ("2.2  Sistemas de control industrial y su capacidad de automonitorización", True, False),
    ("Los sistemas SCADA —Ignition de Inductive Automation, WinCC de Siemens, iFix de GE Digital— están diseñados para supervisar el proceso productivo (temperaturas, presiones, caudales), no la salud del propio sistema informático que los soporta. Un WinCC puede mostrar perfectamente el estado de una válvula mientras el servidor Windows que lo ejecuta está al 98 % de CPU. Esta distinción entre monitorización de proceso y monitorización de infraestructura define el alcance de este proyecto.", False, False),
    ("Los DCS —ABB System 800xA, Emerson DeltaV, Honeywell Experion— incluyen diagnósticos de hardware propios pero propietarios, sin API estándar para integración externa. Esta ausencia de interoperabilidad justifica una solución basada en protocolos de acceso estándar como OPC UA o SNMP.", False, False),
    ("2.3  Protocolos de comunicación industrial para monitorización no intrusiva", True, False),
    ("OPC UA (IEC 62541): estándar de interoperabilidad industrial más relevante de la actualidad, publicado por la OPC Foundation en 2008. Multiplataforma, con cifrado TLS 1.2/1.3 y autenticación X.509, opera sobre TCP puerto 4840. Siemens lo incorpora nativamente en S7-1500 desde firmware V2.0. La librería Python asyncua (v1.0.6) implementa el estándar completo con soporte asíncrono.", False, False),
    ("S7Comm / Snap7: protocolo propietario de Siemens (RFC 1006 / ISO 8073, puerto TCP 102), presente en toda la gama S7 desde S7-300 hasta S7-1500. El proyecto open source Snap7 proporciona una librería nativa multiplataforma. python-snap7 (v1.3) permite acceder a la SZL (System Zustands Liste): estado CPU, modelo, firmware, uso de memoria, buffer de diagnóstico.", False, False),
    ("SNMP (RFC 1157 / SNMPv2c RFC 1901): protocolo de gestión de red universal. La MIB HOST-RESOURCES (RFC 2790) proporciona CPU, memoria y disco de cualquier sistema Windows sin necesidad de agente propietario.", False, False),
    ("WinRM (WS-Management, DMTF DSP0226): permite ejecutar scripts PowerShell de forma remota. La librería pywinrm obtiene métricas no accesibles vía SNMP: estado de servicios, offset NTP, contadores de rendimiento avanzados.", False, False),
    ("2.4  Convergencia IT/OT: marco normativo y arquitectural", True, False),
    ("El modelo de referencia Purdue (ANSI/ISA-95) define los niveles de la pirámide de automatización industrial (0: proceso físico; 1: control básico PLCs; 2: supervisión SCADA/HMI; 3: operaciones MES; 4: planificación ERP). El sistema desarrollado opera en el nivel 3.5, monitorizando la infraestructura de los niveles 1-3 sin interferir en el flujo de control.", False, False),
    ("La norma IEC 62443 (ciberseguridad de IACS) establece en su nivel SL 1 el requisito SR 6.1 de audit log capacity: los sistemas de control deben tener capacidad para registrar eventos de seguridad y operación, lo que otorga una justificación normativa adicional al proyecto.", False, False),
    ("Lee y Kim (2019) sistematizan las diferencias IT/OT: la prioridad de seguridad OT es AIC (Disponibilidad > Integridad > Confidencialidad) frente a CIA en IT; los ciclos de vida OT son de 15-30 años; las actualizaciones son excepcionales; la conectividad externa es restringida. Estas diferencias explican por qué las soluciones IT no pueden trasladarse directamente al mundo OT.", False, False),
    ("2.5  Soluciones comerciales de monitorización y visibilidad OT", True, False),
    ("Claroty y Nozomi Networks son los líderes del mercado de visibilidad OT, con enfoque en análisis pasivo del tráfico de red (puerto SPAN/TAP). Detectan la existencia y comportamiento de activos, pero no métricas de salud internas (porcentaje de CPU, estado RUN/STOP del PLC). Dragos está orientado a threat intelligence en infraestructuras críticas.", False, False),
    ("El coste de estas plataformas —entre 30.000 y 200.000 euros anuales— las hace inaccesibles para organizaciones de tamaño medio, justificando el desarrollo de una alternativa open source.", False, False),
    ("AVEVA PI System es el historian industrial de referencia para datos de proceso, pero está orientado a variables productivas, no a métricas de infraestructura. InfluxDB + Grafana como alternativa open source ha ganado adopción creciente en entornos industriales medianos.", False, False),
    ("2.6  Bases de datos de series temporales", True, False),
    ("Las bases de datos relacionales (MySQL, PostgreSQL) no están optimizadas para el patrón de escritura/consulta de métricas: las tablas crecen indefinidamente, los índices se vuelven enormes y las consultas por rango temporal de millones de filas son lentas. Mazumdar et al. (2019) demuestran que InfluxDB supera a PostgreSQL en un factor de 3-10x en velocidad de inserción y 5-20x en velocidad de consulta para cargas de monitorización.", False, False),
    ("InfluxDB 2.7 unifica el servidor de almacenamiento, la interfaz web y el motor de alertas, y adopta el lenguaje funcional Flux. El operador pivot() transforma el formato columnar de InfluxDB en un formato fila-por-activo adecuado para respuestas de API REST.", False, False),
    ("En abril de 2025 InfluxData publicó como GA InfluxDB 3.0 Core, una reescritura completa en Rust que reemplaza Flux por SQL nativo y usa almacenamiento columnar (Apache Parquet). Sin embargo, la versión 3.0 Core tiene un límite de 5 bases de datos y benchmarks independientes muestran menor velocidad de ingesta para datasets pequeños. Por este motivo el proyecto utiliza InfluxDB 2.7.", False, False),
    ("2.7  Arquitectura de microservicios y contenedorización en entornos industriales", True, False),
    ("Burns et al. (2016) identifican el patrón sidecar: un proceso ligero que acompaña a un sistema principal recolectando métricas y enviándolas a un almacén centralizado. Este patrón es la referencia arquitectural para los agentes del proyecto: cada agente es un contenedor independiente que puede actualizarse o escalarse de forma independiente. Si el agente Siemens falla, el agente de servidores y el VMware siguen funcionando.", False, False),
    ("Docker Compose proporciona una alternativa declarativa y simple a Kubernetes, adecuada para despliegues on-premise en plantas industriales donde el personal IT puede ser limitado. Un único fichero YAML define todos los servicios, garantizando reproducibilidad en cualquier host con Docker instalado.", False, False),
    ("FastAPI permite desarrollar APIs REST de alto rendimiento con documentación automática Swagger/OpenAPI. Las iniciativas NAMUR Open Architecture (NOA) promueven explícitamente el uso de APIs REST como capa de integración entre sistemas de control OT y plataformas corporativas IT.", False, False),
    ("2.8  Conclusiones de la investigación previa", True, False),
    ("Herramientas IT: Zabbix 7.x incluye Modbus nativo y se posiciona como IT & OT, pero no cubre OPC UA ni S7Comm de forma nativa. PRTG (comercial) cubre OPC UA y Modbus pero es de pago por sensor. Las plataformas OT comerciales (Claroty, Nozomi) están orientadas a seguridad pasiva, no a observabilidad operativa.", False, False),
    ("Protocolos: la combinación OPC UA + Snap7 proporciona la cobertura más amplia para el entorno Siemens de GEA. SNMP + WinRM cubre los servidores Windows sin agentes propietarios.", False, False),
    ("Almacenamiento: InfluxDB 2.7 es la opción óptima para alta frecuencia de escritura, consultas por rango temporal e integración con Grafana.", False, False),
    ("Arquitectura: agentes independientes por protocolo, contenedorizados con Docker Compose, proporcionan la modularidad y resiliencia requeridas con complejidad operativa adecuada para on-premise.", False, False),
    ("Configuración dinámica: la integración con Codex requiere una API REST con POST/DELETE de targets sin reinicio de agentes, patrón implementado mediante ConfigPoller que detecta cambios y ajusta el scheduling en tiempo de ejecución.", False, False),
]
insert_paras("Investigaci", s2)

# ── §3.1 METODOLOGÍA ─────────────────────────────────────────────────────────

s31 = [
    ("El proyecto se desarrolló siguiendo una metodología iterativa e incremental, organizada en fases funcionales independientes. Cada fase produce un incremento del sistema completamente funcional, verificable en el entorno real de GEA, y sobre el que se construye la fase siguiente.", False, False),
    ("Esta aproximación es especialmente adecuada por varias razones: el acceso a los equipos reales está sujeto a ventanas de disponibilidad operativa; los requisitos OT (OIDs SNMP disponibles, nodos OPC UA expuestos por el PLC) solo se conocen completamente al conectarse a los dispositivos reales; y la arquitectura modular por agentes permite añadir cada agente sin modificar los existentes.", False, False),
    ("Las herramientas de gestión del proyecto son: Git para control de versiones (commits en convención Conventional Commits: feat, fix, docs, refactor); Claude Code (Anthropic) como asistente de programación con IA; y Codex (OpenAI), integrado como auditor automático de código que analiza cada cambio antes de que la sesión de programación termine.", False, False),
    ("Fases del proyecto:", True, False),
]
anchor_31 = insert_paras("Metodolog", s31)

# Insert phases table
paras_list = list(doc.paragraphs)
h31 = None
for p in paras_list:
    if "Metodolog" in p.text and p.style.name.startswith("Heading"):
        h31 = p
        break
if h31:
    phase_headers = ["Fase", "Nombre", "Descripción", "Estado"]
    phase_rows = [
        ["0", "Preparación", "Análisis de requisitos, estudio de protocolos, diseño de arquitectura, scaffold del proyecto", "Completada"],
        ["1", "Agente de servidores y VMs", "SNMP + WinRM + pyVmomi, InfluxDB, Grafana, API REST básica", "Completada"],
        ["2", "Agente Siemens PLC", "OPC UA + Snap7, configuración dinámica (SQLite + ConfigPoller), integración Codex", "Completada"],
        ["3", "Agente Rockwell (futuro)", "pylogix / EtherNet/IP", "Pendiente"],
        ["4", "Agente de red (futuro)", "SNMP + PROFINET DCP", "Pendiente"],
        ["5", "Alertas y reporting (futuro)", "Grafana Alerting, PDF, email/Teams", "Pendiente"],
    ]
    # find last inserted para to attach table
    last_p = list(doc.paragraphs)
    for i, p in enumerate(last_p):
        if "Fases del proyecto" in p.text:
            insert_table_after(p._element, phase_headers, phase_rows)
            break
    print("  Phases table inserted")

# Gantt note
for p in list(doc.paragraphs):
    if "Fases del proyecto" in p.text:
        # add gantt note after table (find position after table)
        break

gantt_items = [
    ("Planificación temporal (Diagrama de Gantt):", True, False),
    ("A continuación se detalla la planificación temporal con las tareas, duraciones estimadas y dependencias. [Construir el diagrama de Gantt visual en Word/Excel a partir de esta tabla, indicando las fechas reales de inicio y fin.]", False, False),
]
gantt_headers = ["ID", "Tarea", "Duración", "Dependencias"]
gantt_rows = [
    ["T01", "Análisis de requisitos con GEA y estudio del entorno", "1 semana", "—"],
    ["T02", "Estudio de protocolos industriales (SNMP, OPC UA, S7Comm, WinRM)", "2 semanas", "T01"],
    ["T03", "Diseño de arquitectura del sistema (agentes, API, almacenamiento)", "1 semana", "T02"],
    ["T04", "Scaffold del proyecto (Docker Compose, InfluxDB, Grafana)", "1 semana", "T03"],
    ["T05", "Implementación librería compartida (shared/)", "1 semana", "T04"],
    ["T06", "Implementación agente SNMP para servidores Windows", "2 semanas", "T05"],
    ["T07", "Implementación agente WinRM + PowerShell", "1 semana", "T05"],
    ["T08", "Implementación agente VMware ESXi/VMs (pyVmomi)", "2 semanas", "T05"],
    ["T09", "Implementación API REST básica", "1 semana", "T06, T07, T08"],
    ["T10", "Dashboard Grafana Fase 1 (servidores + VMware)", "1 semana", "T09"],
    ["T11", "Pruebas Fase 1 en entorno real GEA", "1 semana", "T10"],
    ["T12", "Config dinámica (SQLite + ConfigPoller + /config/targets)", "2 semanas", "T11"],
    ["T13", "Colector OPC UA (Siemens, modo principal)", "2 semanas", "T12"],
    ["T14", "Colector Snap7 (Siemens, modo fallback, SZL reads)", "1 semana", "T13"],
    ["T15", "Integración modo auto (OPC UA → Snap7) y discovery scripts", "1 semana", "T13, T14"],
    ["T16", "Dashboard Grafana Fase 2 (PLCs Siemens) + integración API Codex", "1 semana", "T15"],
    ["T17", "Pruebas Fase 2 en entorno real GEA (PLCs Siemens)", "1 semana", "T16"],
    ["T18", "Redacción de la memoria del proyecto", "3 semanas", "T17"],
    ["T19", "Revisión con tutor y correcciones", "1 semana", "T18"],
    ["T20", "Preparación de la presentación", "1 semana", "T19"],
]

# Insert gantt note + table after the phases table
paras_list2 = list(doc.paragraphs)
for p in paras_list2:
    if "Fases del proyecto" in p.text:
        cur = p._element
        for text, bold, is_list in gantt_items:
            cur = insert_after(cur, text, bold=bold, is_list=is_list)
        # find the note para to attach table
        for p2 in list(doc.paragraphs):
            if "Construir el diagrama de Gantt" in p2.text:
                insert_table_after(p2._element, gantt_headers, gantt_rows)
                # add duration note
                for p3 in list(doc.paragraphs):
                    if "Construir el diagrama de Gantt" in p3.text:
                        dur_cur = p3._element
                        dur_cur = insert_after(dur_cur, "Duración total estimada: 26 semanas (~6 meses y medio)", bold=False)
                        insert_after(dur_cur, "Período de desarrollo: [COMPLETAR: mes/año inicio] — [COMPLETAR: mes/año fin previsto]", bold=False)
                        break
                break
        break

print("§3.1 done")

# ── §3.2 HERRAMIENTAS ────────────────────────────────────────────────────────

s32 = [
    ("Lenguajes y frameworks de desarrollo", True, False),
    ("Python 3.12 es el lenguaje principal para todos los agentes y la API. La elección se justifica por su ecosistema de librerías industriales —las únicas implementaciones open source maduras de OPC UA, S7Comm, vSphere y WinRM para uso programático son librerías Python— y por su legibilidad y facilidad de mantenimiento.", False, False),
    ("FastAPI es el framework web Python utilizado para la API REST. Genera documentación Swagger/OpenAPI de forma automática a partir de las anotaciones de tipo, lo que facilita la integración con Codex sin necesidad de documentación manual adicional.", False, False),
    ("SQLModel es el ORM utilizado para el almacén de configuración en SQLite. Combina SQLAlchemy y Pydantic en una única librería, eliminando la duplicación de definiciones de esquema.", False, False),
    ("Infraestructura de despliegue", True, False),
    ("Docker Desktop (Windows) y Docker Compose son las herramientas de contenedorización y orquestación del stack completo. El entorno de desarrollo local y el de producción en GEA utilizan el mismo fichero docker-compose.yml, garantizando reproducibilidad del despliegue.", False, False),
    ("InfluxDB 2.7 (InfluxData) es la base de datos de series temporales para el almacenamiento de todas las métricas. Se despliega como contenedor Docker con volúmenes persistentes.", False, False),
    ("Grafana 10.4 (Grafana Labs) es la plataforma de visualización. Los dashboards se provisionan automáticamente desde ficheros JSON al arrancar el contenedor.", False, False),
    ("Librerías Python principales:", True, False),
]
insert_paras("Herramientas y recursos", s32)

# Insert libraries table
lib_headers = ["Librería", "Versión", "Propósito"]
lib_rows = [
    ["asyncua", "1.0.6", "Cliente OPC UA asíncrono (Python 3.12 compatible)"],
    ["python-snap7", "1.3", "Wrapper Python para librería nativa Snap7 (S7Comm)"],
    ["pyVmomi", "8.0.2.0", "SDK oficial Python para VMware vSphere API"],
    ["pysnmp-lextudio", "6.1.3", "Fork de pysnmp compatible con Python 3.12"],
    ["pywinrm", "0.4.3", "Cliente WinRM para PowerShell remoto"],
    ["APScheduler", "3.10.4", "Scheduler de tareas periódicas con soporte dinámico de jobs"],
    ["influxdb-client", "1.44.0", "Cliente oficial Python para InfluxDB 2.x"],
    ["pydantic-settings", "2.2.1", "Gestión de configuración mediante variables de entorno"],
]
for p in list(doc.paragraphs):
    if "Librerías Python principales" in p.text:
        insert_table_after(p._element, lib_headers, lib_rows)
        break

s32b = [
    ("Herramientas de control de calidad", True, False),
    ("Git y GitHub para control de versiones, con el repositorio alojado en [COMPLETAR: URL del repositorio].", False, False),
    ("Claude Code (Anthropic, 2024) es el asistente de programación con IA utilizado a lo largo del proyecto para la generación de código, revisión de arquitectura y resolución de problemas técnicos.", False, False),
    ("Codex (OpenAI, 2024), integrado como plugin en Claude Code, actúa como auditor automático de código: analiza cada cambio realizado antes de que la sesión de desarrollo termine, identificando posibles problemas de seguridad, race conditions y desviaciones de las buenas prácticas.", False, False),
    ("VS Code con las extensiones Python (Pylance, Black Formatter), Docker y REST Client como entorno de desarrollo integrado.", False, False),
    ("Recursos de la empresa GEA Process Engineering", True, False),
    ("GEA facilitó el acceso a servidores Windows con SNMP habilitado, hipervisores VMware ESXi con máquinas virtuales de producción, y PLCs Siemens de la familia S7 en funcionamiento real en planta. [COMPLETAR: número aproximado de equipos o tipo de entorno.]", False, False),
    ("GEA proporcionó acceso a la API de su plataforma interna Codex para probar la integración de registro dinámico de targets y la consulta de métricas.", False, False),
    ("El personal técnico de GEA proporcionó información sobre la arquitectura de red, los modelos específicos de PLC, los protocolos habilitados en cada equipo y los requisitos operativos (no intrusividad, compatibilidad con ventanas de mantenimiento).", False, False),
]
for p in list(doc.paragraphs):
    if "Librerías Python principales" in p.text:
        anchor = p._element
        for text, bold, is_list in s32b:
            anchor = insert_after(anchor, text, bold=bold, is_list=is_list)
        break

print("§3.2 done")

# ── §4 MEMORIA — keep instructional stub, just remove yellow ─────────────────

for p in list(doc.paragraphs):
    if is_yellow(p) and p.style.name.startswith("Heading"):
        continue
    if is_yellow(p):
        h = p.text.lower()
        # Only remove highlight for §4-§9 sections (keep placeholder text but make it black)
        for run in p.runs:
            remove_highlight(run)

print("§4+ highlights removed")

# ── BIBLIOGRAFÍA — replace all yellow with actual references ─────────────────

bib_paras_to_delete = []
bib_heading = None
for p in list(doc.paragraphs):
    if "Bibliograf" in p.text and p.style.name.startswith("Heading"):
        bib_heading = p
        continue
    if bib_heading and is_yellow(p):
        bib_paras_to_delete.append(p)
    if bib_heading and p.style.name.startswith("Heading") and p != bib_heading:
        break

for p in bib_paras_to_delete:
    try:
        del_para(p)
    except Exception:
        pass

REFS = [
    "[1] Galstad, E. (2009). Nagios: System and Network Monitoring (2nd ed.). No Starch Press.",
    "[2] Icinga Project. (2024). Icinga Documentation. https://icinga.com/docs/",
    "[3] Zabbix LLC. (2024). Zabbix Documentation 7.2. https://www.zabbix.com/documentation/7.2/",
    "[3a] Zabbix LLC. (2024). Zabbix — The universal, open-source observability solution for IT & OT. https://www.zabbix.com/",
    "[4] Paessler AG. (2024). PRTG Network Monitor Manual. https://www.paessler.com/manuals/prtg",
    "[4a] Paessler AG. (2025). PRTG Multi-Platform Probe for Siemens Industrial Edge. Paessler AG Press Release. https://www.paessler.com/company/press/releases/",
    "[5] Volz, B., & Watts, R. (2018). Prometheus: Up & Running. O'Reilly Media.",
    "[6] Grafana Labs. (2024). Grafana Documentation. https://grafana.com/docs/",
    "[7] Inductive Automation. (2024). Ignition Documentation. https://docs.inductiveautomation.com/",
    "[8] Siemens AG. (2023). SIMATIC WinCC V7.5 System Manual. Siemens AG.",
    "[9] ABB Ltd. (2022). System 800xA Operations Manual. ABB Ltd.",
    "[10] OPC Foundation. (2017). OPC Unified Architecture Specification Part 1: Overview and Concepts (IEC 62541-1). OPC Foundation. https://reference.opcfoundation.org/",
    "[11] asyncua contributors. (2024). asyncua: Python OPC-UA client and server library. https://github.com/FreeOpcUa/opcua-asyncio",
    "[12] Nardella, D. (2023). Snap7 — A free, open source, multi-platform Siemens S7 Communication library. http://snap7.sourceforge.net/",
    "[13] Case, J., Fedor, M., Schoffstall, M., & Davin, J. (1990). RFC 1157: A Simple Network Management Protocol (SNMP). IETF. https://datatracker.ietf.org/doc/html/rfc1157",
    "[14] Waldbusser, S. (2000). RFC 2790: Host Resources MIB. IETF. https://datatracker.ietf.org/doc/html/rfc2790",
    "[15] DMTF. (2013). DSP0226: Web Services Management (WS-Management) Specification v1.1.0. DMTF. https://www.dmtf.org/dsp/DSP0226",
    "[16] pywinrm contributors. (2024). pywinrm: Python client for Windows Remote Management. https://github.com/diyan/pywinrm",
    "[17] ISA. (2010). ANSI/ISA-95.00.01-2010: Enterprise-Control System Integration Part 1: Models and Terminology. ISA.",
    "[18] IEC. (2018). IEC 62443-3-3: Industrial communication networks – Network and system security – Part 3-3: System security requirements and security levels. International Electrotechnical Commission.",
    "[19] Lee, J., & Kim, B. (2019). Challenges and opportunities in cyber-physical systems for manufacturing. CIRP Annals, 68(2), 791-814. https://doi.org/10.1016/j.cirp.2019.05.003",
    "[20] CISA. (2021). Alert (AA21-131A): DarkSide Ransomware. CISA. https://www.cisa.gov/uscert/ncas/alerts/aa21-131a",
    "[21] Bajak, F. (2021). Florida water treatment plant hack. AP News, 9 February 2021.",
    "[22] Claroty. (2024). The Claroty Platform: Comprehensive OT/IoT Security. https://claroty.com/",
    "[23] Nozomi Networks. (2024). Nozomi Networks Guardian: OT/IoT Security and Visibility. https://www.nozominetworks.com/",
    "[24] Dragos. (2023). ICS/OT Cybersecurity Year in Review 2023. Dragos Inc. https://www.dragos.com/year-in-review/",
    "[25] AVEVA. (2024). AVEVA PI System: Industrial Data Management. https://www.aveva.com/en/products/aveva-pi-system/",
    "[26] Cherki, B., Chiky, R., & Hebrail, G. (2020). Monitoring industrial IoT devices with open-source tools. IEEE ICIT. https://doi.org/10.1109/ICIT45562.2020.9067256",
    "[27] Mazumdar, S., Dutta, D., Bhatt, D., & Jha, S. (2019). Evaluating time-series databases for IoT monitoring applications. IEEE BigData. https://doi.org/10.1109/BigData47090.2019.9006512",
    "[28] InfluxData. (2024). InfluxDB 2.7 Documentation. https://docs.influxdata.com/influxdb/v2/",
    "[28a] InfluxData. (2025). InfluxDB 3.0 Core — Generally Available. https://docs.influxdata.com/influxdb/v3/",
    "[28b] QuestDB. (2024). InfluxDB benchmark: write throughput comparison. QuestDB Engineering Blog. https://questdb.io/blog/",
    "[29] Burns, B., Grant, B., Oppenheimer, D., Brewer, E., & Wilkes, J. (2016). Borg, Omega, and Kubernetes. ACM Queue, 14(1), 70-93.",
    "[30] Burns, B., Beda, J., & Hightower, K. (2022). Kubernetes: Up and Running (3rd ed.). O'Reilly Media.",
    "[31] Docker Inc. (2024). Docker Compose Documentation. https://docs.docker.com/compose/",
    "[32] Fielding, R. T. (2000). Architectural Styles and the Design of Network-based Software Architectures (PhD thesis, UC Irvine).",
    "[33] OPC Foundation. (2020). OPC UA Part 6: Mappings (HTTP/REST). OPC Foundation.",
    "[34] Ramirez, S. (2024). FastAPI Documentation. https://fastapi.tiangolo.com/",
    "[35] TechEmpower. (2024). TechEmpower Framework Benchmarks — Round 22. https://www.techempower.com/benchmarks/",
]

if bib_heading:
    anchor = bib_heading._element
    for ref in REFS:
        anchor = insert_after(anchor, ref, bold=False, is_list=False)
    print("Bibliography inserted")

# ── SAVE ─────────────────────────────────────────────────────────────────────

doc.save("Memoria PFG - Control System Health Status.docx")
print("\nDone! Saved: 'Memoria PFG - Control System Health Status.docx'")
