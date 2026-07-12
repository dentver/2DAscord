from dataclasses import dataclass, field, asdict
from typing import Optional


# ── Модели данных ───────────────────────────────────────


@dataclass
class Message:
    sender: str
    avatar: str
    text: str


@dataclass
class ParticipantInfo:
    name: str
    avatar: str


class ClientConnection:
    def __init__(self, writer, reader, name: str, avatar: str):
        self.writer = writer
        self.reader = reader
        self.name = name
        self.avatar = avatar
