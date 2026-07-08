class P2PProtocol:
    CMD_HELLO = "HELLO"
    CMD_WELCOME = "WELCOME"
    CMD_SEND_M = "MESSAGE"
    CMD_DIST_M = "DISTRIBUTION"
    CMD_PAR_JOIN = "PARTICIPANT_JOIN"

    @staticmethod
    def encode(cmd: str, *args) -> bytes:
        message = cmd
        for arg in args:
            message += "|" + str(arg)
        message += "\n"
        return message.encode("utf-8")

    @staticmethod
    def decode(data: bytes) -> tuple:
        line = data.decode("utf-8").strip()
        parts = line.split("|")
        cmd = parts[0]
        args = parts[1:] if len(parts) > 1 else []
        return cmd, args
