import asyncio
import struct
import array
import time

from .signals import P2PSignals
from .voice import JitterBuffer, VoiceEngine
from .voice_protocol import VoiceProtocol
from .voice_transport import VoiceTransport


# ── Voice Controller ─────────────────────────────────


INTERVAL = VoiceEngine.FRAME_SIZE / VoiceEngine.SAMPLERATE


class VoiceController:
    def __init__(self, signals: P2PSignals):
        self.signals = signals
        self.transport: VoiceTransport | None = None
        self.engine: VoiceEngine | None = None
        self.jitters: dict[int, JitterBuffer] = {}
        self.endpoints: dict[tuple, int] = {}
        self.host_voice_addr: tuple | None = None
        self.client_voice_jitter: JitterBuffer | None = None
        self.running: bool = False
        self.send_task: asyncio.Task | None = None
        self.decode_task: asyncio.Task | None = None

    async def start_transport(self) -> int:
        from .logger import step_start, step_ok, step_fail
        if self.transport:
            step_ok("VOICE_TRANSPORT", "already running")
            return self.transport.port
        step_start("VOICE_TRANSPORT", "starting UDP transport")
        try:
            self.transport = VoiceTransport()
            await self.transport.start()
            self.transport.on_packet = self.on_packet
            step_ok("VOICE_TRANSPORT", f"port={self.transport.port}")
            return self.transport.port
        except Exception as e:
            step_fail("VOICE_TRANSPORT", str(e))
            raise

    def get_port(self) -> int:
        return self.transport.port if self.transport else 0

    def register_endpoint(self, addr: tuple, client_id: int):
        self.endpoints[addr] = client_id

    def unregister_endpoint(self, addr: tuple):
        self.endpoints.pop(addr, None)

    def remove_endpoint_by_client_id(self, client_id: int):
        for addr, cid in list(self.endpoints.items()):
            if cid == client_id:
                self.endpoints.pop(addr, None)
                return

    def create_client_jitter(self, client_id: int) -> JitterBuffer:
        jb = JitterBuffer()
        self.jitters[client_id] = jb
        return jb

    def remove_jitter(self, client_id: int):
        self.jitters.pop(client_id, None)

    def set_host_addr(self, addr: tuple):
        self.host_voice_addr = addr

    def set_client_jitter(self, jb: JitterBuffer):
        self.client_voice_jitter = jb

    def on_packet(self, pkt: dict, addr: tuple):
        if pkt['magic'] != VoiceProtocol.MAGIC:
            return
        if self.client_voice_jitter is not None:
            self.client_voice_jitter.add(pkt['seq'], pkt['payload'])
        else:
            client_id = self.endpoints.get(addr)
            if client_id is not None:
                jitter = self.jitters.get(client_id)
                if jitter:
                    jitter.add(pkt['seq'], pkt['payload'])

    def warmup_audio(self):
        from .logger import step_start, step_ok
        step_start("WARMUP", "warming audio device")
        if not self.engine:
            self.engine = VoiceEngine()
        self.engine.warmup()
        step_ok("WARMUP", "done")

    async def enable(self):
        from .logger import step_start, step_ok
        step_start("VOICE_ENABLE", "enable called")
        if not self.engine:
            self.engine = VoiceEngine()
        self.engine.start()
        if not self.running:
            self.running = True
            self.send_task = asyncio.create_task(self._send_loop())
            self.decode_task = asyncio.create_task(self._decode_loop())
        self.engine.muted = False
        self.signals.voice_state_changed.emit(True)
        step_ok("VOICE_ENABLE", "mic enabled")

    async def disable(self):
        from .logger import step_ok
        if self.engine:
            self.engine.muted = True
        self.signals.voice_state_changed.emit(False)
        step_ok("VOICE_DISABLE", "mic disabled")

    async def cleanup(self):
        from .logger import step_start, step_ok
        step_start("VOICE_CLEANUP", "cleaning up")
        self.running = False
        if self.send_task:
            self.send_task.cancel()
            self.send_task = None
        if self.decode_task:
            self.decode_task.cancel()
            self.decode_task = None
        if self.engine:
            self.engine.stop()
            self.engine = None
        if self.transport:
            self.transport.close()
            self.transport = None
        self.jitters.clear()
        self.endpoints.clear()
        self.host_voice_addr = None
        self.client_voice_jitter = None
        step_ok("VOICE_CLEANUP", "done")

    async def _send_loop(self):
        from .logger import step_fail
        seq = 0
        next_tick = time.monotonic()
        while self.running:
            next_tick += INTERVAL
            try:
                frame = self.engine.get_encoded_frame_nowait()
                if frame:
                    timestamp = int(time.time() * 1000)
                    packet = VoiceProtocol.encode(frame, seq, timestamp)
                    if self.endpoints:
                        for addr in list(self.endpoints.keys()):
                            self.transport.send(packet, addr)
                    elif self.host_voice_addr:
                        self.transport.send(packet, self.host_voice_addr)
                    seq += 1
            except Exception as e:
                step_fail("SEND_LOOP", str(e))
            now = time.monotonic()
            sleep_for = next_tick - now
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)

    async def _decode_loop(self):
        from .logger import step_fail
        next_tick = time.monotonic()
        while self.running:
            next_tick += INTERVAL
            try:
                if self.client_voice_jitter is not None:
                    pkt = self.client_voice_jitter.pop()
                    if pkt and self.engine:
                        self.engine.put_pcm_bytes(pkt)
                else:
                    mixed = [0] * VoiceEngine.FRAME_SIZE
                    has_audio = False
                    for jitter in list(self.jitters.values()):
                        pkt = jitter.pop()
                        if pkt and self.engine:
                            n = len(pkt) // 2
                            if n == 0:
                                continue
                            arr = list(
                                struct.unpack(f'{n}h', pkt)
                            )
                            limit = min(n, VoiceEngine.FRAME_SIZE)
                            for i in range(limit):
                                s = mixed[i] + arr[i]
                                if s > 32767:
                                    s = 32767
                                elif s < -32768:
                                    s = -32768
                                mixed[i] = s
                            has_audio = True
                    if has_audio and self.engine:
                        self.engine.put_pcm_frame(array.array('h', mixed))
            except Exception as e:
                step_fail("DECODE_LOOP", str(e))
            now = time.monotonic()
            sleep_for = next_tick - now
            if sleep_for > 0:
                await asyncio.sleep(sleep_for)
