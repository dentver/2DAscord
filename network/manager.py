import asyncio
import logging

from .protocol import P2PProtocol
from .upnp import SessionCreator

logger = logging.getLogger(__name__)


class P2PManager:
    @staticmethod
    async def start_server():
        room_code, host_ip, tcp_port = SessionCreator.open("TCP")
        logger.info("Код комнаты: %s", room_code)
        logger.info("Внешний IP для клиентов: %s:%d", host_ip, tcp_port)
        logger.info("Запуск сервера на порту %d...", tcp_port)
        server = await asyncio.start_server(P2PManager.server_chat, "0.0.0.0", tcp_port)
        logger.info("Сервер запущен на порту %d", tcp_port)
        asyncio.create_task(server.serve_forever())
        return server, [room_code, host_ip, tcp_port]

    @staticmethod
    async def server_chat(reader, writer):
        try:
            while True:
                data = await reader.read(102400)
                if not data:
                    break

                cmd, args = P2PProtocol.decode(data)

                if cmd == P2PProtocol.CMD_HELLO:
                    return

                writer.write(data)
                await writer.drain()
        except ConnectionResetError:
            pass
        finally:
            writer.close()
            await writer.wait_closed()

    @staticmethod
    async def client(room_code: str, host_ip: str, host_port: int, name: str) -> None:
        writer = None
        try:
            while True:
                should_exit = False
                reader, writer = await asyncio.open_connection(host_ip, host_port)
                hello_msg = P2PProtocol.encode(P2PProtocol.CMD_HELLO, room_code, name)
                writer.write(hello_msg)
                await writer.drain()

                data = await reader.readline()
                cmd, args = P2PProtocol.decode(data)

                if should_exit:
                    break
        finally:
            if writer:
                writer.close()
                await writer.wait_closed()
