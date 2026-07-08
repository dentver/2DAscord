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

        cls._server = await asyncio.start_server(cls._handle_client, "0.0.0.0", tcp_port)
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
                sender = cls._clients[client_id]

                msg = Message(sender=sender.name, avatar=sender.avatar, text=text)
                cls._messages.append(msg)
                cls._messages = cls._messages[-50:]

                dist = P2PProtocol.encode(
                    P2PProtocol.CMD_DIST_M, sender.name, sender.avatar, text
                )
                await cls._broadcast(dist, exclude={client_id})
                cls.signals.message_received.emit(sender.name, sender.avatar, text)

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
    async def host_send_message(cls, text: str) -> None:
        host = cls._clients.get(0)
        if not host:
            return

        msg = Message(sender=host.name, avatar=host.avatar, text=text)
        cls._messages.append(msg)
        cls._messages = cls._messages[-50:]

        dist = P2PProtocol.encode(
            P2PProtocol.CMD_DIST_M, host.name, host.avatar, text
        )
        await cls._broadcast(dist, exclude={0})
        cls.signals.message_received.emit(host.name, host.avatar, text)

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
            reader, writer = await asyncio.open_connection(host_ip, host_port)

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
        except Exception:
            pass
        finally:
            cls.signals.disconnected.emit()

    @classmethod
    async def client_send_message(cls, text: str) -> None:
        if cls._client_writer:
            try:
                msg = P2PProtocol.encode(P2PProtocol.CMD_SEND_M, text)
                cls._client_writer.write(msg)
                await cls._client_writer.drain()
                cls.signals.message_received.emit(
                    cls._client_name, cls._client_avatar, text
                )
            except Exception:
                cls.signals.connection_failed.emit("Ошибка отправки сообщения")
