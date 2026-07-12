# API Documentation

## network.manager — P2PManager

Central class managing both server and client sides of the P2P connection.

### Class Attributes

| Attribute          | Type                      | Description                        |
|--------------------|---------------------------|------------------------------------|
| `signals`          | `P2PSignals`              | Qt signals for UI events           |
| `_clients`         | `dict[int, ClientConnection]` | Connected clients (server side)    |
| `_messages`        | `list[Message]`           | Recent messages (up to 50)         |
| `_room_code`       | `str`                     | Current room code                  |
| `_next_id`         | `int`                     | Next client ID                     |
| `_server`          | `asyncio.AbstractServer`  | Server instance                    |
| `_tcp_port`        | `int`                     | Listening port                     |
| `_client_reader`   | `asyncio.StreamReader`    | Client reader                      |
| `_client_writer`   | `asyncio.StreamWriter`    | Client writer                      |
| `_client_name`     | `str`                     | Client's nickname                  |
| `_client_avatar`   | `str`                     | Client's base64 avatar             |

### Host Methods

#### `start_server(host_name: str, host_avatar: str) -> None`
Creates a UPnP session, binds a TCP server, and starts accepting clients.

#### `host_send_message(text: str, avatar: str = "", name: str = "") -> None`
Sends a message from the host to all connected clients.

#### `host_update_avatar(avatar: str) -> None`
Broadcasts an avatar change from the host.

#### `stop_server() -> None`
Closes all client connections, removes the UPnP port mapping, and shuts down the server.

### Client Methods

#### `connect(host_ip: str, host_port: int, room_code: str, name: str, avatar: str) -> None`
Connects to a remote host using the provided IP, port, and room code. Sends a `HELLO` handshake and awaits a `WELCOME` response.

#### `client_send_message(text: str, avatar: str = "", name: str = "") -> None`
Sends a chat message to the host. Updates local avatar/name if changed.

#### `client_update_avatar(avatar: str) -> None`
Sends an avatar update to the host.

#### `disconnect() -> None`
Closes the client connection and emits the `disconnected` signal.

### Internal Methods

#### `_handle_client(reader, writer) -> None`
Accepts incoming client connections, validates the room code, assigns an ID, sends welcome data, and enters the read loop.

#### `_client_read_loop(client_id: int, reader) -> None`
Reads messages from a connected client and processes `SEND_M`, `AVATAR` commands.

#### `_client_receive_loop(reader) -> None`
Reads incoming data from the server and dispatches to the appropriate signal.

#### `_broadcast(data: bytes, exclude: set = None) -> None`
Sends raw data to all connected clients except those in the exclude set.

---

## network.protocol — P2PProtocol

Wire protocol using JSON + newline encoding.

### Commands

| Constant       | Value       | Direction       | Description                    |
|----------------|-------------|-----------------|--------------------------------|
| `CMD_HELLO`    | `"HELLO"`   | Client → Host   | Handshake with room code       |
| `CMD_WELCOME`  | `"WELCOME"` | Host → Client   | Participants + message history |
| `CMD_SEND_M`   | `"SEND_M"`  | Client → Host   | Incoming message               |
| `CMD_DIST_M`   | `"DIST_M"`  | Host → Clients  | Distribute message             |
| `CMD_PAR_JOIN` | `"PAR_JOIN"`| Host → Clients  | New participant joined         |
| `CMD_PAR_LEAVE`| `"PAR_LEAVE"`| Host → Clients | Participant left               |
| `CMD_AVATAR`   | `"AVATAR"`  | Bidirectional   | Avatar update                  |
| `CMD_NAME`     | `"NAME"`    | Host → Clients  | Name change                    |

### Methods

#### `encode(cmd: str, *args) -> bytes`
Serializes command and arguments to `[cmd, ...args]\n` JSON bytes.

#### `decode(data: bytes) -> tuple`
Parses a JSON line into `(cmd, args_list)`.

---

## network.signals — P2PSignals

Qt signals emitted by `P2PManager`. Inherits `QObject`.

| Signal                         | Args                                    | Description                      |
|--------------------------------|-----------------------------------------|----------------------------------|
| `session_created`              | `(str, str, int)`                       | Room code, public IP, port       |
| `welcome_received`             | `(str, list, list)`                     | My name, participants, messages  |
| `message_received`             | `(str, str, str)`                       | Sender name, avatar, text        |
| `participant_joined`           | `(str, str)`                            | Name, avatar                     |
| `participant_left`             | `(str)`                                 | Name                             |
| `participant_avatar_updated`   | `(str, str)`                            | Name, new avatar                 |
| `participant_name_updated`     | `(str, str)`                            | Old name, new name               |
| `connection_failed`            | `(str)`                                 | Error message                    |
| `disconnected`                 | `()`                                    | Client disconnected              |
| `session_ended`                | `()`                                    | Server session ended             |

---

## network.upnp — SessionCreator

Handles UPnP port forwarding, room code generation, and public IP discovery.

### Methods

#### `get_room_code() -> str`
Generates a random 7-character alphanumeric room code.

#### `get_host_ip() -> str`
Returns the public IP via `api.ipify.org`.

#### `init_port(protocol: str) -> int`
Finds an available port (49152–65535) and attempts UPnP mapping.

#### `local_check_port(port: int) -> bool`
Checks if a TCP port is free on localhost.

#### `router_check_port(port: int, protocol: str, description: str, lease_duration: int) -> bool`
Maps a port on the router via UPnP.

#### `remove_port_mapping(port: int, protocol: str) -> bool`
Removes a UPnP port mapping.

#### `open(protocol: str) -> list`
Convenience: returns `[room_code, public_ip, port]`.

---

## network.models — Data Models

### `Message`
- `sender: str` — nickname
- `avatar: str` — base64 PNG
- `text: str` — message content

### `ParticipantInfo`
- `name: str`
- `avatar: str`

### `ClientConnection`
- `writer: StreamWriter`
- `reader: StreamReader`
- `name: str`
- `avatar: str`

---

## ui.main_window — MainWindow

Main application window built with PyQt5. Manages all UI elements and connects to `P2PManager` signals.

### Key UI Sections

- **Connect frame** — create/join session, room code display, IP labels
- **Join frame** — IP:Port and room code input for connecting
- **Members list** — online participants with avatars
- **Chat display** — rendered HTML chat with right-aligned own messages
- **Profile** — avatar selection (rounded), nickname input
- **Voice** — microphone and screen share buttons (placeholder)

### Key Callbacks

| Method                        | Trigger                               |
|-------------------------------|---------------------------------------|
| `_new_session()`              | "Создать сессию" button               |
| `_connection()`               | "Подключиться" button (join frame)    |
| `_send_message()`             | Send button / Enter key               |
| `_end_session()`              | "Завершить сессию" button (host)      |
| `_disconnect()`               | "Отключиться" button (client)         |

### Signal Slots

| Slot                          | Signal                                     |
|-------------------------------|--------------------------------------------|
| `_on_session_created`         | `P2PManager.signals.session_created`       |
| `_on_welcome_received`        | `P2PManager.signals.welcome_received`      |
| `_on_message_received`        | `P2PManager.signals.message_received`      |
| `_on_participant_joined`      | `P2PManager.signals.participant_joined`    |
| `_on_participant_left`        | `P2PManager.signals.participant_left`      |
| `_on_participant_avatar_updated` | `P2PManager.signals.participant_avatar_updated` |
| `_on_participant_name_updated`   | `P2PManager.signals.participant_name_updated` |
| `_on_connection_failed`       | `P2PManager.signals.connection_failed`     |
| `_on_disconnected`            | `P2PManager.signals.disconnected`          |
| `_on_session_ended`           | `P2PManager.signals.session_ended`         |

---

## utils.avatar — Avatar Utilities

Helper functions for avatar manipulation.

| Function                         | Description                               |
|----------------------------------|-------------------------------------------|
| `make_round_pixmap(pixmap, size)` | Crops a `QPixmap` into a circle           |
| `load_avatar_b64(file_path)`      | Reads an image file → base64 string       |
| `b64_to_pixmap(b64)`              | Decodes base64 → `QPixmap`               |
| `make_round_b64(b64, size)`       | Decodes, rounds, re-encodes to base64    |
| `set_round_pixmap_on_label(...)`  | Sets a rounded pixmap on a `QLabel`      |
| `load_from_file_and_display(...)` | Loads file → displays on label → returns base64 |
| `select_avatar(parent, label)`    | Opens file dialog → returns base64       |
| `load_default_avatar(label)`      | Loads `resources/account.png`            |
