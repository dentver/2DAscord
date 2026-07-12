# 2DAscord

Децентрализованный peer-to-peer чат с голосовой связью. Никаких серверов — всё работает напрямую между участниками через UPnP.

## Возможности

- **P2P-чат** — обмен текстовыми сообщениями без посредников
- **Создание сессий** — автоматический проброс портов (UPnP), код комнаты, внешний/LAN/локальный адрес
- **Подключение** — по IP:Port и коду сессии
- **Аватары** — загрузка PNG/JPG, автоматическое скругление
- **Никнеймы** — смена ника в реальном времени, синхронизация с участниками
- **Список участников** — онлайн-статус, аватары, имена
- **Голосовая связь** — микрофон и демонстрация экрана (заготовка)
- **Тёмная тема** — стилизованный интерфейс в стиле Discord
- **Кроссплатформенность** — Windows, Linux, macOS

## Технологии

| Компонент      | Технология     |
|----------------|----------------|
| GUI            | PyQt5          |
| Асинхронность  | asyncio + qasync |
| Сеть           | asyncio TCP    |
| UPnP           | miniupnpc      |
| Изображения    | Pillow         |
| Сборка         | PyInstaller    |
| Установщик     | Inno Setup     |

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
├── main.py                  # Точка входа
├── network/
│   ├── manager.py           # P2PManager — сервер/клиент
│   ├── protocol.py          # P2PProtocol — кодирование команд
│   ├── signals.py           # P2PSignals — сигналы Qt
│   ├── models.py            # Модели данных
│   └── upnp.py              # SessionCreator — UPnP, комнаты, IP
├── ui/
│   └── main_window.py       # MainWindow — интерфейс
├── utils/
│   └── avatar.py            # Работа с аватарами
├── resources/
│   ├── main.css             # Стили
│   ├── 2DAicon.png          # Иконка
│   └── account.png          # Аватар по умолчанию
└── docs/
    └── api.md               # API-документация
```
