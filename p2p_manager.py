import asyncio
from upnp_utils import Create_Session
from p2p_protocol import P2PProtocol

class p2pManager:
    @staticmethod
    async def start_server():
        room_code, host_ip, tcp_port = Create_Session.open("TCP")
        print(f"Код комнаты: {room_code}")
        print(f"Внешний IP для клиентов: {host_ip}:{tcp_port}")
        print(f"Запуск сервера на порту {tcp_port}...")
        server = await asyncio.start_server(p2pManager.server_chat, '0.0.0.0', tcp_port)
        
        print(f"Сервер запущен на порту {tcp_port}")
        
        asyncio.create_task(server.serve_forever())
        
        return server, [room_code, host_ip, tcp_port]
    
    @staticmethod        
    async def server_chat(reader, writer):
        try:
            while True:
                data = await reader.read(102400) # Читаем до 100 килобайт
                if not data:
                    break # Клиент отключился

                cmd, args = P2PProtocol.decode(data)

                if cmd == P2PProtocol.CMD_HELLO:
                    return

                # Отправляем данные обратно
                writer.write(data)
                await writer.drain() # Очищаем буфер отправки
        except ConnectionResetError:
            pass
        finally:
            writer.close()
            await writer.wait_closed() 
    
    @staticmethod
    async def client(room_code, host_ip, host_port, name):
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