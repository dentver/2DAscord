import json


class P2PProtocol:
    CMD_HELLO = "HELLO"
    CMD_WELCOME = "WELCOME"
    CMD_SEND_M = "SEND_M"
    CMD_DIST_M = "DIST_M"
    CMD_PAR_JOIN = "PAR_JOIN"
    CMD_PAR_LEAVE = "PAR_LEAVE"

    @staticmethod
    def encode(cmd: str, *args) -> bytes:
        data = json.dumps([cmd, *args], ensure_ascii=False)
        return data.encode("utf-8") + b"\n"

    @staticmethod
    def decode(data: bytes) -> tuple:
        parts = json.loads(data.decode("utf-8").strip())
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
