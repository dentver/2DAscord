import asyncio
import json

from .protocol import P2PProtocol
from .upnp import SessionCreator
from .signals import P2PSignals
from .models import ClientConnection, Message
from .voice_controller import VoiceController
from .ssl_utils import generate_self_signed_cert, create_server_ssl_context, get_rsa_key


# ── P2P Host ─────────────────────────────────────────


class P2PHost:
    def __init__(self, signals: P2PSignals, voice: VoiceController):
        self.signals = signals
        self.voice = voice
        self.clients: dict[int, ClientConnection] = {}
        self.messages: list[Message] = []
        self.room_code: str = ""
        self.next_id: int = 1
        self.server = None
        self.tcp_port: int = 0

    async def start(self, host_name: str, host_avatar: str) -> None:
        from .logger import step_start, step_ok, step_fail
        step_start("HOST_START", f"name={host_name}")

        self.messages.clear()
        self.clients.clear()
        self.next_id = 1
        step_ok("HOST_START", "state cleared")

        room_code = SessionCreator.get_room_code()
        tcp_port = SessionCreator.find_local_port()
        step_ok("HOST_START", f"port found: {tcp_port}")

        if not tcp_port:
            step_fail("HOST_START", "no port available")
            raise RuntimeError("Не удалось найти свободный порт для подключения")

        self.room_code = room_code
        self.clients[0] = ClientConnection(
            writer=None, reader=None, name=host_name, avatar=host_avatar
        )
        step_ok("HOST_START", "room/clients set")

        try:
            step_start("HOST_START", "getting RSA key")
            key = await get_rsa_key()
            step_ok("HOST_START", "RSA key obtained")

            cert_pem, key_pem = generate_self_signed_cert(key)
            step_ok("HOST_START", "cert generated")

            server_ctx = create_server_ssl_context(cert_pem, key_pem)
            step_ok("HOST_START", "SSL context created")

            self.server = await asyncio.start_server(
                self._handle_client, "0.0.0.0", tcp_port,
                ssl=server_ctx, limit=1024*1024
            )
            step_ok("HOST_START", f"TCP server on port {tcp_port}")
            self.tcp_port = tcp_port

            self.voice.warmup_audio()
            step_ok("HOST_START", "audio warmup done")

            await self.voice.start_transport()
            step_ok("HOST_START", "voice transport started")

            self.signals.session_created.emit(room_code, "", tcp_port)
            step_ok("HOST_START", "session_created signal emitted")

            asyncio.create_task(self._background_setup())
            asyncio.create_task(self._heartbeat_loop())
            step_ok("HOST_START", "background tasks started")

            await self.server.serve_forever()
        except Exception as e:
            step_fail("HOST_START", f"error: {e}")
            if self.tcp_port:
                SessionCreator.remove_port_mapping(self.tcp_port, "TCP")
            self.clients.clear()
            self.messages.clear()
            self.room_code = ""
            self.next_id = 1
            raise

    async def _background_setup(self):
        from .logger import step_start, step_ok, step_fail, step_exc
        step_start("BG_SETUP", "fetching IP and UPnP")
        try:
            host_ip = await SessionCreator.get_host_ip_async()
            await SessionCreator.setup_upnp(self.tcp_port)
            if host_ip:
                self.signals.external_ip_ready.emit(host_ip)
                step_ok("BG_SETUP", f"IP={host_ip}")
            else:
                step_fail("BG_SETUP", "no external IP")
        except Exception as e:
            step_exc("BG_SETUP", e)

    async def _heartbeat_loop(self):
        while True:
            await asyncio.sleep(45)
            ping = P2PProtocol.encode(P2PProtocol.CMD_PING)
            await self._broadcast(ping, exclude=set())

    async def _handle_client(self, reader, writer) -> None:
        client_id = None
        try:
            data = await reader.readline()
            if not data:
                return

            cmd, args = P2PProtocol.decode(data)

            if cmd != P2PProtocol.CMD_HELLO:
                writer.close()
                return

            client_code, client_name, client_avatar = args

            if client_code != self.room_code:
                writer.close()
                return

            client_id = self.next_id
            self.next_id += 1
            self.clients[client_id] = ClientConnection(
                writer=writer, reader=reader, name=client_name, avatar=client_avatar
            )

            participants = [
                {"name": c.name, "avatar": c.avatar}
                for c in self.clients.values()
            ]
            messages = [
                {"sender": m.sender, "avatar": m.avatar, "text": m.text}
                for m in self.messages
            ]

            welcome = P2PProtocol.encode(
                P2PProtocol.CMD_WELCOME,
                json.dumps(participants, ensure_ascii=False),
                json.dumps(messages, ensure_ascii=False)
            )
            writer.write(welcome)
            await writer.drain()

            voice_port = self.voice.get_port()
            if voice_port:
                voice_port_cmd = P2PProtocol.encode(
                    P2PProtocol.CMD_VOICE_PORT, str(voice_port)
                )
                writer.write(voice_port_cmd)
                await writer.drain()

            join_msg = P2PProtocol.encode(
                P2PProtocol.CMD_PAR_JOIN, client_name, client_avatar
            )
            await self._broadcast(join_msg, exclude={0, client_id})
            self.signals.participant_joined.emit(client_name, client_avatar)

            await self._client_read_loop(client_id, reader)

        except asyncio.CancelledError:
            pass
        except Exception:
            pass
        finally:
            if client_id and client_id in self.clients:
                client = self.clients.pop(client_id)
                self.voice.remove_jitter(client_id)
                self.voice.remove_endpoint_by_client_id(client_id)
                leave_msg = P2PProtocol.encode(
                    P2PProtocol.CMD_PAR_LEAVE, client.name
                )
                await self._broadcast(leave_msg, exclude={0})
                self.signals.participant_left.emit(client.name)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    async def _client_read_loop(self, client_id: int, reader) -> None:
        while True:
            data = await reader.readline()
            if not data:
                break

            try:
                cmd, args = P2PProtocol.decode(data)
            except Exception:
                continue

            if cmd == P2PProtocol.CMD_SEND_M:
                text = args[0]
                avatar = args[1] if len(args) > 1 else ""
                sender = self.clients[client_id]
                current_avatar = avatar or sender.avatar
                if avatar and avatar != sender.avatar:
                    self.clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=sender.name, avatar=avatar
                    )
                    self.signals.participant_avatar_updated.emit(sender.name, avatar)
                    sender = self.clients[client_id]

                new_name = args[2] if len(args) > 2 else ""
                current_name = new_name or sender.name
                if new_name and new_name != sender.name:
                    old_name = sender.name
                    self.clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=new_name, avatar=current_avatar
                    )
                    self.signals.participant_name_updated.emit(old_name, new_name)
                    name_cmd = P2PProtocol.encode(
                        P2PProtocol.CMD_NAME, old_name, new_name
                    )
                    await self._broadcast(name_cmd, exclude={client_id})
                    sender = self.clients[client_id]

                msg = Message(sender=current_name, avatar=current_avatar, text=text)
                self.messages.append(msg)
                self.messages = self.messages[-50:]

                dist = P2PProtocol.encode(
                    P2PProtocol.CMD_DIST_M, current_name, current_avatar, text
                )
                await self._broadcast(dist, exclude={client_id})
                self.signals.message_received.emit(current_name, current_avatar, text)

            elif cmd == P2PProtocol.CMD_AVATAR:
                avatar = args[0] if args else ""
                if avatar:
                    sender = self.clients[client_id]
                    self.clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=sender.name, avatar=avatar
                    )
                    self.signals.participant_avatar_updated.emit(sender.name, avatar)
                    avatar_cmd = P2PProtocol.encode(
                        P2PProtocol.CMD_AVATAR, sender.name, avatar
                    )
                    await self._broadcast(avatar_cmd, exclude={client_id})

            elif cmd == P2PProtocol.CMD_VOICE_READY:
                client_port = int(args[0])
                client = self.clients.get(client_id)
                if client and client.writer:
                    peername = client.writer.get_extra_info('peername')
                    if peername:
                        addr = (peername[0], client_port)
                        self.voice.register_endpoint(addr, client_id)
                        self.voice.create_client_jitter(client_id)

    async def _broadcast(self, data: bytes, exclude: set = None) -> None:
        if exclude is None:
            exclude = set()
        for cid, client in list(self.clients.items()):
            if cid in exclude:
                continue
            if client.writer:
                try:
                    client.writer.write(data)
                    await client.writer.drain()
                except Exception:
                    pass

    async def send_message(self, text: str, avatar: str = "", name: str = "") -> None:
        host = self.clients.get(0)
        if not host:
            return

        avatar = avatar or host.avatar
        if avatar != host.avatar:
            self.clients[0] = ClientConnection(
                writer=host.writer, reader=host.reader,
                name=host.name, avatar=avatar
            )
            self.signals.participant_avatar_updated.emit(host.name, avatar)
            host = self.clients[0]

        current_name = name or host.name
        if name and name != host.name:
            old_name = host.name
            self.clients[0] = ClientConnection(
                writer=host.writer, reader=host.reader,
                name=name, avatar=host.avatar
            )
            self.signals.participant_name_updated.emit(old_name, name)
            name_cmd = P2PProtocol.encode(P2PProtocol.CMD_NAME, old_name, name)
            await self._broadcast(name_cmd, exclude={0})
            host = self.clients[0]

        msg = Message(sender=current_name, avatar=avatar, text=text)
        self.messages.append(msg)
        self.messages = self.messages[-50:]

        dist = P2PProtocol.encode(
            P2PProtocol.CMD_DIST_M, current_name, avatar, text
        )
        await self._broadcast(dist, exclude={0})
        self.signals.message_received.emit(current_name, avatar, text)

    async def update_avatar(self, avatar: str) -> None:
        host = self.clients.get(0)
        if not host or avatar == host.avatar:
            return
        self.clients[0] = ClientConnection(
            writer=host.writer, reader=host.reader,
            name=host.name, avatar=avatar
        )
        self.signals.participant_avatar_updated.emit(host.name, avatar)
        avatar_cmd = P2PProtocol.encode(P2PProtocol.CMD_AVATAR, host.name, avatar)
        await self._broadcast(avatar_cmd, exclude={0})

    async def stop(self) -> None:
        try:
            await self.voice.cleanup()
        except Exception:
            pass
        for cid, client in list(self.clients.items()):
            if cid != 0 and client.writer:
                try:
                    client.writer.close()
                    await client.writer.wait_closed()
                except Exception:
                    pass

        if self.tcp_port:
            SessionCreator.remove_port_mapping(self.tcp_port, "TCP")
            self.tcp_port = 0

        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self.server = None

        self.clients.clear()
        self.messages.clear()
        self.room_code = ""
        self.next_id = 1

        self.signals.session_ended.emit()
