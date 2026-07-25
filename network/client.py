import asyncio
import json

from .protocol import P2PProtocol
from .signals import P2PSignals
from .voice import JitterBuffer
from .voice_controller import VoiceController
from .ssl_utils import create_client_ssl_context


# ── P2P Client ───────────────────────────────────────


class P2PClient:
    def __init__(self, signals: P2PSignals, voice: VoiceController):
        self.signals = signals
        self.voice = voice
        self.reader = None
        self.writer = None
        self.my_name: str = ""
        self.my_avatar: str = ""
        self.host_connect_ip: str = ""
        self.room_code: str = ""

    def is_connected(self) -> bool:
        return self.writer is not None

    async def connect(
        self, host_ip: str, host_port: int, room_code: str,
        name: str, avatar: str
    ) -> None:
        from .logger import step_start, step_ok, step_fail
        step_start("CLIENT_CONNECT", f"{host_ip}:{host_port} room={room_code}")
        writer = None
        ssl_ctx = create_client_ssl_context()
        try:
            step_start("CLIENT_CONNECT", "opening TCP/SSL connection")
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(
                    host_ip, host_port, ssl=ssl_ctx, limit=1024*1024
                ),
                timeout=10
            )
            step_ok("CLIENT_CONNECT", "TCP/SSL connected")

            hello = P2PProtocol.encode(
                P2PProtocol.CMD_HELLO, room_code, name, avatar
            )
            writer.write(hello)
            await writer.drain()
            step_ok("CLIENT_CONNECT", "HELLO sent")

            data = await reader.readline()
            if not data:
                step_fail("CLIENT_CONNECT", "no response from host")
                self.signals.connection_failed.emit("Нет ответа от хоста")
                return

            cmd, args = P2PProtocol.decode(data)
            step_ok("CLIENT_CONNECT", f"got {cmd}")

            if cmd == P2PProtocol.CMD_WELCOME:
                participants = json.loads(args[0])
                messages = json.loads(args[1])
                step_ok("CLIENT_CONNECT", f"welcome: {len(participants)} participants, {len(messages)} messages")

                self.reader = reader
                self.writer = writer
                self.my_name = name
                self.my_avatar = avatar
                self.host_connect_ip = host_ip
                self.room_code = room_code

                self.signals.welcome_received.emit(name, participants, messages)

                await self._receive_loop(reader)
            else:
                step_fail("CLIENT_CONNECT", f"unexpected cmd: {cmd}")
                self.signals.connection_failed.emit(
                    f"Неизвестный ответ от хоста: {cmd}"
                )
                return

        except (OSError, asyncio.TimeoutError) as e:
            step_fail("CLIENT_CONNECT", f"net error: {e}")
            self.signals.connection_failed.emit(str(e))
        except Exception as e:
            step_fail("CLIENT_CONNECT", f"error: {e}")
            self.signals.connection_failed.emit(str(e))
        finally:
            self.reader = None
            self.writer = None
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    async def _receive_loop(self, reader) -> None:
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                try:
                    cmd, args = P2PProtocol.decode(data)
                except Exception:
                    continue

                if cmd == P2PProtocol.CMD_DIST_M:
                    sender, avatar_b64, text = args
                    self.signals.message_received.emit(sender, avatar_b64, text)
                elif cmd == P2PProtocol.CMD_PAR_JOIN:
                    name, avatar_b64 = args
                    self.signals.participant_joined.emit(name, avatar_b64)
                elif cmd == P2PProtocol.CMD_PAR_LEAVE:
                    name = args[0]
                    self.signals.participant_left.emit(name)
                elif cmd == P2PProtocol.CMD_AVATAR:
                    sender, avatar_b64 = args
                    self.signals.participant_avatar_updated.emit(sender, avatar_b64)
                elif cmd == P2PProtocol.CMD_NAME:
                    old_name, new_name = args
                    self.signals.participant_name_updated.emit(old_name, new_name)
                elif cmd == P2PProtocol.CMD_PING:
                    pass
                elif cmd == P2PProtocol.CMD_VOICE_PORT:
                    voice_port = int(args[0])
                    self.voice.warmup_audio()
                    await self.voice.start_transport()
                    self.voice.set_host_addr((self.host_connect_ip, voice_port))
                    self.voice.set_client_jitter(JitterBuffer())
                    if self.writer:
                        ready = P2PProtocol.encode(
                            P2PProtocol.CMD_VOICE_READY,
                            str(self.voice.get_port())
                        )
                        self.writer.write(ready)
                        await self.writer.drain()
        except Exception:
            pass
        finally:
            self.signals.disconnected.emit()

    async def send_message(self, text: str, avatar: str = "", name: str = "") -> None:
        if self.writer:
            try:
                current_avatar = avatar or self.my_avatar
                if current_avatar != self.my_avatar:
                    self.my_avatar = current_avatar
                current_name = name or self.my_name
                if name and name != self.my_name:
                    old_name = self.my_name
                    self.my_name = name
                    self.signals.participant_name_updated.emit(old_name, name)
                    msg = P2PProtocol.encode(P2PProtocol.CMD_SEND_M, text, current_avatar, name)
                else:
                    msg = P2PProtocol.encode(P2PProtocol.CMD_SEND_M, text, current_avatar)
                self.writer.write(msg)
                await self.writer.drain()
                self.signals.message_received.emit(
                    current_name, current_avatar, text
                )
            except Exception:
                self.signals.connection_failed.emit("Ошибка отправки сообщения")

    async def update_avatar(self, avatar: str) -> None:
        if self.writer and avatar and avatar != self.my_avatar:
            self.my_avatar = avatar
            msg = P2PProtocol.encode(P2PProtocol.CMD_AVATAR, avatar)
            self.writer.write(msg)
            await self.writer.drain()

    async def disconnect(self) -> None:
        await self.voice.cleanup()
        if self.writer:
            try:
                self.writer.close()
                await self.writer.wait_closed()
            except Exception:
                pass
        self.reader = None
        self.writer = None
        self.my_name = ""
        self.my_avatar = ""
        self.room_code = ""
        self.signals.disconnected.emit()
