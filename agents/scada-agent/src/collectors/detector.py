import logging

from asyncua import Client

logger = logging.getLogger(__name__)

_SERVER_NODE = "ns=0;i=2253"


def classify_scada_text(text: str) -> str:
    value = text.lower()
    if "ignition" in value or "inductive automation" in value:
        return "Ignition"
    if "wincc" in value or "siemens" in value:
        return "WinCC"
    if "factorytalk" in value or "rockwell" in value:
        return "FactoryTalk"
    if "aveva" in value or "wonderware" in value or "system platform" in value:
        return "AVEVA"
    return "unknown"


async def detect_scada_type(url: str, username: str | None = None, password: str | None = None, timeout: int = 10) -> str:
    try:
        client = Client(url=url, timeout=timeout)
        if username and password:
            client.set_user(username)
            client.set_password(password)
        async with client:
            texts = [url]
            try:
                server = client.get_node(_SERVER_NODE)
                attrs = await server.read_attributes([])
                texts.extend(str(a) for a in attrs)
            except Exception:
                pass
            try:
                status = await client.nodes.server.get_child("0:ServerStatus")
                build_info = await status.get_child("0:BuildInfo")
                app = await build_info.read_value()
                texts.append(str(app))
            except Exception:
                pass
            return classify_scada_text(" ".join(texts))
    except Exception as exc:
        logger.debug("scada_detect_failed url=%s error=%s", url, exc)
        return "unknown"
