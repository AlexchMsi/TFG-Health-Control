"""
Servidor OPC UA de simulación para validar siemens-agent y scada-agent en local.

Expone:
  - ServerStatus estándar (ns=0;i=2259) — lo que lee el siemens-agent (method=opcua).
  - Variables de proceso con NodeId de texto predecible — lo que lee el scada-agent:
        ns=2;s=Temperature   (float, cambia cada 2 s)
        ns=2;s=Pressure      (float, cambia cada 2 s)
        ns=2;s=PumpRunning   (bool)
        ns=2;s=LineStatus    (string)

Uso (reutilizando la imagen del siemens-agent, que ya incluye asyncua):

    docker run -d --name opcua-sim --network ftg_ot-health-net \
        -v ./scripts:/sim ftg-siemens-agent python /sim/opcua_sim_server.py

Después, registrar targets apuntando a opc.tcp://opcua-sim:4840.
"""

import asyncio
import logging
import random

from asyncua import Server, ua

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("opcua-sim")


async def main() -> None:
    server = Server()
    await server.init()
    server.set_endpoint("opc.tcp://0.0.0.0:4840/")
    server.set_server_name("FTG Simulated OPC UA Server")

    idx = await server.register_namespace("http://ftg.sim")
    process = await server.nodes.objects.add_object(idx, "Process")

    temperature = await process.add_variable(
        ua.NodeId("Temperature", idx), ua.QualifiedName("Temperature", idx), 21.5
    )
    pressure = await process.add_variable(
        ua.NodeId("Pressure", idx), ua.QualifiedName("Pressure", idx), 1.0
    )
    pump = await process.add_variable(
        ua.NodeId("PumpRunning", idx), ua.QualifiedName("PumpRunning", idx), True
    )
    line_status = await process.add_variable(
        ua.NodeId("LineStatus", idx), ua.QualifiedName("LineStatus", idx), "OK"
    )

    logger.info("OPC UA sim server listening on 0.0.0.0:4840 (namespace index=%d)", idx)

    async with server:
        while True:
            await temperature.write_value(round(20.0 + random.random() * 5.0, 2))
            await pressure.write_value(round(0.9 + random.random() * 0.3, 3))
            await pump.write_value(random.random() > 0.1)
            await line_status.write_value("OK" if random.random() > 0.05 else "DEGRADED")
            await asyncio.sleep(2)


if __name__ == "__main__":
    asyncio.run(main())
