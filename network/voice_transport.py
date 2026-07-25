import asyncio
from .voice_protocol import VoiceProtocol


# ── Voice Transport (UDP) ─────────────────────────────


class VoiceDatagramProtocol(asyncio.DatagramProtocol):
    def __init__(self, transport_owner):
        self._owner = transport_owner

    def datagram_received(self, data, addr):
        try:
            pkt = VoiceProtocol.decode(data)
        except Exception:
            return
        if pkt['magic'] != VoiceProtocol.MAGIC:
            return
        self._owner._on_packet(pkt, addr)

    def error_received(self, exc):
        pass


class VoiceTransport:
    def __init__(self):
        self._transport: asyncio.DatagramTransport | None = None
        self.port: int = 0
        self.on_packet = None

    async def start(self):
        loop = asyncio.get_event_loop()
        self._transport, _ = await loop.create_datagram_endpoint(
            lambda: VoiceDatagramProtocol(self),
            local_addr=('0.0.0.0', 0)
        )
        self.port = self._transport.get_extra_info('sockname')[1]

    def send(self, data: bytes, addr: tuple):
        if self._transport:
            try:
                self._transport.sendto(data, addr)
            except Exception:
                pass

    def close(self):
        if self._transport:
            self._transport.close()
            self._transport = None

    def _on_packet(self, pkt: dict, addr: tuple):
        if self.on_packet:
            self.on_packet(pkt, addr)
