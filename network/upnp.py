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
        return requests.get("https://api.ipify.org").text.strip()

    @staticmethod
    def init_port(protocol: str) -> int:
        port_start = 49152
        port_end = 65535
        for i in range(port_start, port_end):
            if SessionCreator.local_check_port(i):
                if SessionCreator.router_check_port(i, protocol):
                    return i

    @staticmethod
    def local_check_port(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return True
            except OSError:
                return False

    @staticmethod
    def router_check_port(port: int, protocol: str, description: str = "2DAscord", lease_duration: int = 3600) -> bool:
        try:
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200

            devices_count = upnp.discover()
            if devices_count == 0:
                return False

            upnp.selectigd()
            local_ip = upnp.lanaddr

            try:
                upnp.deleteportmapping(port, protocol)
            except Exception:
                pass

            result = upnp.addportmapping(port, protocol, local_ip, port, description, "")

            if result:
                try:
                    upnp.getspecificportmapping(port, protocol)
                except Exception:
                    pass
                return True
            else:
                return False

        except Exception:
            return False

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

    @staticmethod
    def open(protocol: str = "TCP") -> list:
        return [
            SessionCreator.get_room_code(),
            SessionCreator.get_host_ip(),
            SessionCreator.init_port(protocol)
        ]
