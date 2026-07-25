import asyncio
import random
import string
import socket
import requests
import miniupnpc


# ── UPnP и сессии ───────────────────────────────────────


class SessionCreator:
    @staticmethod
    def get_room_code() -> str:
        symbols = string.ascii_letters + string.digits
        return "".join(random.choices(symbols, k=7))

    @staticmethod
    def get_host_ip() -> str:
        from .logger import step_start, step_ok, step_fail
        step_start("HOST_IP", "fetching external IP")
        try:
            r = requests.get("https://api.ipify.org", timeout=3)
            ip = r.text.strip()
            step_ok("HOST_IP", f"got {ip}")
            return ip
        except Exception as e:
            step_fail("HOST_IP", str(e))
            return ""

    @staticmethod
    async def get_host_ip_async() -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, SessionCreator.get_host_ip)

    @staticmethod
    def find_local_port() -> int:
        from .logger import step_start, step_ok, step_fail
        step_start("INIT_PORT", "finding free port")
        for i in range(49152, 65535):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind(("", i))
                    step_ok("INIT_PORT", f"found port {i}")
                    return i
                except OSError:
                    continue
        step_fail("INIT_PORT", "no port available")
        return 0

    @staticmethod
    def _do_upnp(port: int, protocol: str) -> bool:
        try:
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200
            devices_count = upnp.discover()
            if devices_count == 0:
                return False
            upnp.selectigd()
            try:
                upnp.deleteportmapping(port, protocol)
            except Exception:
                pass
            return upnp.addportmapping(port, protocol, upnp.lanaddr, port, "2DAscord", "")
        except Exception:
            return False

    @staticmethod
    async def setup_upnp(port: int, protocol: str = "TCP") -> bool:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, SessionCreator._do_upnp, port, protocol)

    @staticmethod
    def remove_port_mapping(port: int, protocol: str) -> bool:
        try:
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200
            devices_count = upnp.discover()
            if devices_count == 0:
                return False
            upnp.selectigd()
            upnp.deleteportmapping(port, protocol)
            return True
        except Exception:
            return False
