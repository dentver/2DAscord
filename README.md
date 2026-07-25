# 2DAscord

Децентрализованный peer-to-peer чат с голосовой связью. Никаких серверов — всё работает напрямую между участниками через UPnP.

## Возможности

- **P2P-чат** — обмен текстовыми сообщениями без посредников
- **Создание сессий** — автоматический проброс портов (UPnP), код комнаты, внешний/LAN/локальный адрес
- **Подключение** — по IP:Port и коду сессии
- **Аватары** — загрузка PNG/JPG, автоматическое скругление
- **Никнеймы** — смена ника в реальном времени, синхронизация с участниками
- **Список участников** — онлайн-статус, аватары, имена
- **Голосовая связь** — микрофон (P2P UDP, Opus-подобный фреймворк)
- **Системные уведомления** — всплывающие подсказки в центре экрана
- **Копирование адресов** — клик по IP/LAN/коду сессии копирует в буфер
- **Тёмная тема** — стилизованный интерфейс в стиле Discord
- **Кроссплатформенность** — Windows, Linux, macOS

## Технологии

| Компонент       | Технология      |
|-----------------|-----------------|
| GUI             | PyQt5           |
| Асинхронность   | asyncio + qasync |
| Сеть            | asyncio TCP + UDP |
| Шифрование      | TLS (самоподписанный сертификат) |
| Криптография    | cryptography (RSA-2048) |
| UPnP            | miniupnpc       |
| Аудио           | sounddevice + PortAudio |
| Изображения     | Pillow          |
| Сборка          | PyInstaller     |
| Установщик      | Inno Setup      |

## Запуск из исходного кода

```bash
python -m venv venv
source venv/bin/activate     # Linux/macOS
venv\Scripts\activate        # Windows

pip install -r requirements.txt
python main.py
```

## Структура проекта

```
2DAscord/
├── main.py                     # Точка входа, глобальный хук исключений
├── network/
│   ├── manager.py              # P2PManager — фасад (делегирует Host/Client/Voice)
│   ├── host.py                 # P2PHost — серверная логика (TCP, клиенты, heartbeat)
│   ├── client.py               # P2PClient — клиентская логика (подключение, приём)
│   ├── protocol.py             # P2PProtocol — кодирование/декодирование команд
│   ├── signals.py              # P2PSignals — сигналы Qt
│   ├── models.py               # Модели данных
│   ├── upnp.py                 # SessionCreator — UPnP, комнаты, IP
│   ├── ssl_utils.py            # Генерация RSA-ключа и самоподписанного сертификата
│   ├── voice.py                # VoiceEngine — захват/воспроизведение аудио, VAD
│   ├── voice_controller.py     # VoiceController — управление голосовой сессией
│   ├── voice_protocol.py       # VoiceProtocol — упаковка аудиофреймов
│   ├── voice_transport.py      # VoiceTransport — UDP-транспорт
│   └── logger.py               # Пошаговое логирование в файл
├── ui/
│   └── main_window.py          # MainWindow — интерфейс
├── utils/
│   └── avatar.py               # Работа с аватарами
├── resources/
│   ├── main.css                # Стили
│   ├── 2DAicon.png             # Иконка
│   └── account.png             # Аватар по умолчанию
└── docs/
    └── api.md                  # API-документация
```
