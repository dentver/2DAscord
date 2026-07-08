import asyncio
import json
import logging

from .protocol import P2PProtocol
from .upnp import SessionCreator
from .signals import P2PSignals
from .models import ClientConnection, Message, ParticipantInfo

logger = logging.getLogger(__name__)


class P2PManager:
    signals = P2PSignals()

    _clients: dict[int, ClientConnection] = {}
    _messages: list[Message] = []
    _room_code: str = ""
    _next_id: int = 1

    _server = None
    _tcp_port: int = 0

    _client_reader = None
    _client_writer = None
    _client_name: str = ""
    _client_avatar: str = ""

    # ── Host ─────────────────────────────────────────────

    @classmethod
    async def start_server(cls, host_name: str, host_avatar: str) -> None:
        cls._messages.clear()
        cls._clients.clear()
        cls._next_id = 1

        room_code, host_ip, tcp_port = SessionCreator.open("TCP")
        cls._room_code = room_code

        cls._clients[0] = ClientConnection(
            writer=None, reader=None, name=host_name, avatar=host_avatar
        )

        cls.signals.session_created.emit(room_code, host_ip, tcp_port)

        cls._server = await asyncio.start_server(cls._handle_client, "0.0.0.0", tcp_port, limit=1024*1024)
        cls._tcp_port = tcp_port
        await cls._server.serve_forever()

    @classmethod
    async def _handle_client(cls, reader, writer) -> None:
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

            if client_code != cls._room_code:
                writer.close()
                return

            client_id = cls._next_id
            cls._next_id += 1
            cls._clients[client_id] = ClientConnection(
                writer=writer, reader=reader, name=client_name, avatar=client_avatar
            )

            participants = [
                {"name": c.name, "avatar": c.avatar}
                for c in cls._clients.values()
            ]
            messages = [
                {"sender": m.sender, "avatar": m.avatar, "text": m.text}
                for m in cls._messages
            ]

            welcome = P2PProtocol.encode(
                P2PProtocol.CMD_WELCOME,
                json.dumps(participants, ensure_ascii=False),
                json.dumps(messages, ensure_ascii=False)
            )
            writer.write(welcome)
            await writer.drain()

            join_msg = P2PProtocol.encode(
                P2PProtocol.CMD_PAR_JOIN, client_name, client_avatar
            )
            await cls._broadcast(join_msg, exclude={0, client_id})
            cls.signals.participant_joined.emit(client_name, client_avatar)

            await cls._client_read_loop(client_id, reader)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception("Ошибка handle_client: %s", e)
        finally:
            if client_id and client_id in cls._clients:
                client = cls._clients.pop(client_id)
                leave_msg = P2PProtocol.encode(
                    P2PProtocol.CMD_PAR_LEAVE, client.name
                )
                await cls._broadcast(leave_msg, exclude={0})
                cls.signals.participant_left.emit(client.name)
            try:
                writer.close()
                await writer.wait_closed()
            except Exception:
                pass

    @classmethod
    async def _client_read_loop(cls, client_id: int, reader) -> None:
        while True:
            data = await reader.readline()
            if not data:
                break

            cmd, args = P2PProtocol.decode(data)

            if cmd == P2PProtocol.CMD_SEND_M:
                text = args[0]
                avatar = args[1] if len(args) > 1 else ""
                sender = cls._clients[client_id]
                current_avatar = avatar or sender.avatar
                if avatar and avatar != sender.avatar:
                    cls._clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=sender.name, avatar=avatar
                    )
                    cls.signals.participant_avatar_updated.emit(sender.name, avatar)
                    sender = cls._clients[client_id]

                new_name = args[2] if len(args) > 2 else ""
                current_name = new_name or sender.name
                if new_name and new_name != sender.name:
                    old_name = sender.name
                    cls._clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=new_name, avatar=current_avatar
                    )
                    cls.signals.participant_name_updated.emit(old_name, new_name)
                    nm = P2PProtocol.encode(
                        P2PProtocol.CMD_NAME, old_name, new_name
                    )
                    await cls._broadcast(nm, exclude={client_id})
                    sender = cls._clients[client_id]

                msg = Message(sender=current_name, avatar=current_avatar, text=text)
                cls._messages.append(msg)
                cls._messages = cls._messages[-50:]

                dist = P2PProtocol.encode(
                    P2PProtocol.CMD_DIST_M, current_name, current_avatar, text
                )
                await cls._broadcast(dist, exclude={client_id})
                cls.signals.message_received.emit(current_name, current_avatar, text)

            elif cmd == P2PProtocol.CMD_AVATAR:
                avatar = args[0] if args else ""
                if avatar:
                    sender = cls._clients[client_id]
                    cls._clients[client_id] = ClientConnection(
                        writer=sender.writer, reader=sender.reader,
                        name=sender.name, avatar=avatar
                    )
                    cls.signals.participant_avatar_updated.emit(sender.name, avatar)
                    avt = P2PProtocol.encode(
                        P2PProtocol.CMD_AVATAR, sender.name, avatar
                    )
                    await cls._broadcast(avt, exclude={client_id})

    @classmethod
    async def _broadcast(cls, data: bytes, exclude: set = None) -> None:
        if exclude is None:
            exclude = set()
        for cid, client in list(cls._clients.items()):
            if cid in exclude:
                continue
            if client.writer:
                try:
                    client.writer.write(data)
                    await client.writer.drain()
                except Exception:
                    pass

    @classmethod
    async def host_send_message(cls, text: str, avatar: str = "", name: str = "") -> None:
        host = cls._clients.get(0)
        if not host:
            return

        avatar = avatar or host.avatar
        if avatar != host.avatar:
            cls._clients[0] = ClientConnection(
                writer=host.writer, reader=host.reader,
                name=host.name, avatar=avatar
            )
            cls.signals.participant_avatar_updated.emit(host.name, avatar)
            host = cls._clients[0]

        current_name = name or host.name
        if name and name != host.name:
            old_name = host.name
            cls._clients[0] = ClientConnection(
                writer=host.writer, reader=host.reader,
                name=name, avatar=host.avatar
            )
            cls.signals.participant_name_updated.emit(old_name, name)
            nm = P2PProtocol.encode(P2PProtocol.CMD_NAME, old_name, name)
            await cls._broadcast(nm, exclude={0})
            host = cls._clients[0]

        msg = Message(sender=current_name, avatar=avatar, text=text)
        cls._messages.append(msg)
        cls._messages = cls._messages[-50:]

        dist = P2PProtocol.encode(
            P2PProtocol.CMD_DIST_M, current_name, avatar, text
        )
        await cls._broadcast(dist, exclude={0})
        cls.signals.message_received.emit(current_name, avatar, text)

    @classmethod
    async def host_update_avatar(cls, avatar: str) -> None:
        host = cls._clients.get(0)
        if not host or avatar == host.avatar:
            return
        cls._clients[0] = ClientConnection(
            writer=host.writer, reader=host.reader,
            name=host.name, avatar=avatar
        )
        cls.signals.participant_avatar_updated.emit(host.name, avatar)
        avt = P2PProtocol.encode(P2PProtocol.CMD_AVATAR, host.name, avatar)
        await cls._broadcast(avt, exclude={0})

    @classmethod
    async def stop_server(cls) -> None:
        logger.info("Завершение сессии...")

        for cid, client in list(cls._clients.items()):
            if cid != 0 and client.writer:
                try:
                    client.writer.close()
                    await client.writer.wait_closed()
                except Exception:
                    pass

        if cls._tcp_port:
            SessionCreator.remove_port_mapping(cls._tcp_port, "TCP")
            cls._tcp_port = 0

        if cls._server:
            cls._server.close()
            await cls._server.wait_closed()
            cls._server = None

        cls._clients.clear()
        cls._messages.clear()
        cls._room_code = ""
        cls._next_id = 1

        cls.signals.session_ended.emit()
        logger.info("Сессия завершена")

    # ── Client ───────────────────────────────────────────

    @classmethod
    async def connect(
        cls, host_ip: str, host_port: int, room_code: str,
        name: str, avatar: str
    ) -> None:
        writer = None
        try:
            reader, writer = await asyncio.open_connection(host_ip, host_port, limit=1024*1024)

            hello = P2PProtocol.encode(
                P2PProtocol.CMD_HELLO, room_code, name, avatar
            )
            writer.write(hello)
            await writer.drain()

            data = await reader.readline()
            if not data:
                cls.signals.connection_failed.emit("Нет ответа от хоста")
                return

            cmd, args = P2PProtocol.decode(data)

            if cmd == P2PProtocol.CMD_WELCOME:
                participants = json.loads(args[0])
                messages = json.loads(args[1])

                cls._client_reader = reader
                cls._client_writer = writer
                cls._client_name = name
                cls._client_avatar = avatar

                cls.signals.welcome_received.emit(name, participants, messages)

                await cls._client_receive_loop(reader)

        except (OSError, asyncio.TimeoutError) as e:
            cls.signals.connection_failed.emit(str(e))
        except Exception as e:
            cls.signals.connection_failed.emit(str(e))
        finally:
            cls._client_reader = None
            cls._client_writer = None
            if writer:
                try:
                    writer.close()
                    await writer.wait_closed()
                except Exception:
                    pass

    @classmethod
    async def _client_receive_loop(cls, reader) -> None:
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break

                cmd, args = P2PProtocol.decode(data)

                if cmd == P2PProtocol.CMD_DIST_M:
                    sender, avatar_b64, text = args
                    cls.signals.message_received.emit(sender, avatar_b64, text)
                elif cmd == P2PProtocol.CMD_PAR_JOIN:
                    name, avatar_b64 = args
                    cls.signals.participant_joined.emit(name, avatar_b64)
                elif cmd == P2PProtocol.CMD_PAR_LEAVE:
                    name = args[0]
                    cls.signals.participant_left.emit(name)
                elif cmd == P2PProtocol.CMD_AVATAR:
                    sender, avatar_b64 = args
                    cls.signals.participant_avatar_updated.emit(sender, avatar_b64)
                elif cmd == P2PProtocol.CMD_NAME:
                    old_name, new_name = args
                    cls.signals.participant_name_updated.emit(old_name, new_name)
        except Exception:
            pass
        finally:
            cls.signals.disconnected.emit()

    @classmethod
    async def client_send_message(cls, text: str, avatar: str = "", name: str = "") -> None:
        if cls._client_writer:
            try:
                current_avatar = avatar or cls._client_avatar
                if current_avatar != cls._client_avatar:
                    cls._client_avatar = current_avatar
                current_name = name or cls._client_name
                if name and name != cls._client_name:
                    old_name = cls._client_name
                    cls._client_name = name
                    cls.signals.participant_name_updated.emit(old_name, name)
                    msg = P2PProtocol.encode(P2PProtocol.CMD_SEND_M, text, current_avatar, name)
                else:
                    msg = P2PProtocol.encode(P2PProtocol.CMD_SEND_M, text, current_avatar)
                cls._client_writer.write(msg)
                await cls._client_writer.drain()
                cls.signals.message_received.emit(
                    current_name, current_avatar, text
                )
            except Exception:
                cls.signals.connection_failed.emit("Ошибка отправки сообщения")

    @classmethod
    async def client_update_avatar(cls, avatar: str) -> None:
        if cls._client_writer and avatar and avatar != cls._client_avatar:
            cls._client_avatar = avatar
            msg = P2PProtocol.encode(P2PProtocol.CMD_AVATAR, avatar)
            cls._client_writer.write(msg)
            await cls._client_writer.drain()

    @classmethod
    async def disconnect(cls) -> None:
        if cls._client_writer:
            try:
                cls._client_writer.close()
                await cls._client_writer.wait_closed()
            except Exception:
                pass
        cls._client_reader = None
        cls._client_writer = None
        cls._client_name = ""
        cls._client_avatar = ""
        cls._room_code = ""
        cls.signals.disconnected.emit()
