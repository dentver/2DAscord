from dataclasses import dataclass


# ── Data Models ───────────────────────────────────────


@dataclass
class Message:
    sender: str
    avatar: str
    text: str


class ClientConnection:
    def __init__(self, writer, reader, name: str, avatar: str):
        self.writer = writer
        self.reader = reader
        self.name = name
        self.avatar = avatar
