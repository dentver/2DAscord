import random
import requests
import string
import socket
import miniupnpc

class Create_Session:
    @staticmethod
    def get_room_code() -> str: 
        symbols = string.ascii_letters + string.digits
        return ''.join(random.choices(symbols, k=7))

    @staticmethod
    def get_host_ip() -> str:
        return requests.get('https://api.ipify.org').text.strip()

    @staticmethod
    def init_port(protocol: str) -> int:
        port_start = 49152 
        port_end = 65535
        for i in range (port_start, port_end):
            if(Create_Session.local_check_port(i)):
                if(Create_Session.router_check_port(i, protocol)):
                    return i

    @staticmethod
    def local_check_port(port: int) -> bool:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                # Пытаемся привязаться к порту на ВСЕХ интерфейсах ('' = 0.0.0.0)
                s.bind(('', port))
                return True   # bind успешен → порт свободен
            except OSError:
                # Ошибка OSError (например, "Address already in use") → порт занят
                return False

    @staticmethod    
    def router_check_port(port: int, protocol: str, description='2DAscord', lease_duration=3600) -> bool: # сейчас TCP потом буду использовать UDP
        try:
            # 1. Создаём объект UPnP и настраиваем задержку обнаружения
            upnp = miniupnpc.UPnP()
            upnp.discoverdelay = 200  # миллисекунды, даём время на поиск устройств

            # 2. Поиск устройств (возвращает количество найденных)
            devices_count = upnp.discover()
            if devices_count == 0:
                return False

            # 3. Выбираем IGD (Internet Gateway Device)
            upnp.selectigd()

            # 4. Получаем нужные адреса
            local_ip = upnp.lanaddr       # внутренний IP роутера (для проброса)

            # 5. Пытаемся удалить уже существующее правило для этого порта (чтобы избежать конфликта)
            try:
                upnp.deleteportmapping(port, protocol)
            except Exception as e:
                # Если правило не существовало, просто игнорируем ошибку
                print(f"[UPnP] Старое правило не найдено или не удалено: {e}")

            # 6. Добавляем новое правило проброса
            # addportmapping(port, protocol, internal_client, internal_port, description, remote_host)
            result = upnp.addportmapping(port, protocol, local_ip, port, description, '')

            if result:
                print(f"[UPnP] Порт {port} ({protocol}) успешно проброшен на {local_ip}:{port}")
                # Дополнительно: можно проверить создание правила через getportmapping
                try:
                    check = upnp.getspecificportmapping(port, protocol)
                except:
                    print("[UPnP] Не удалось проверить правило, но оно, вероятно, создано.")
                return True
            else:
                return False

        except Exception as e:
            return False

    @staticmethod
    def open(protocol = "TCP") -> list:
        return [Create_Session.get_room_code(),
                Create_Session.get_host_ip(),
                Create_Session.init_port(protocol)]