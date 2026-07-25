# API Documentation

## network.manager — P2PManager

Facade class that delegates all operations to `P2PHost`, `P2PClient`, and `VoiceController`.

### Class Attributes

| Attribute  | Type                  | Description               |
|------------|-----------------------|---------------------------|
| `signals`  | `P2PSignals`          | Qt signals for UI events  |
| `_host`    | `P2PHost`             | Server-side logic         |
| `_client`  | `P2PClient`           | Client-side logic         |
| `_voice`   | `VoiceController`     | Voice session management  |

### Host Methods

#### `start_server(host_name: str, host_avatar: str) -> None`
Creates a session: generates RSA key + self-signed cert, binds TCP/SSL server, starts voice transport, emits `session_created`, launches background IP fetch and UPnP, starts heartbeat.

#### `host_send_message(text: str, avatar: str = "", name: str = "") -> None`
Sends a message from the host to all connected clients. Updates avatar/name on the host if changed.

#### `host_update_avatar(avatar: str) -> None`
Broadcasts an avatar change from the host to all clients.

#### `stop_server() -> None`
Cleans up voice, closes all client connections, removes UPnP mapping, shuts down the server, emits `session_ended`.

### Client Methods

#### `connect(host_ip: str, host_port: int, room_code: str, name: str, avatar: str) -> None`
Opens TCP/SSL connection, sends `HELLO` handshake, awaits `WELCOME` response, then enters receive loop.

#### `client_send_message(text: str, avatar: str = "", name: str = "") -> None`
Sends a chat message to the host. Updates local avatar/name if changed.

#### `client_update_avatar(avatar: str) -> None`
Sends an avatar update to the host.

#### `disconnect() -> None`
Cleans up voice, closes the connection, emits `disconnected`.

#### `is_connected() -> bool`
Returns `True` if the client has an active writer.

### Voice Methods

#### `enable_voice() -> None`
Starts the audio engine, launches send/decode loops, unmutes the microphone, emits `voice_state_changed(True)`.

#### `disable_voice() -> None`
Mutes the microphone, emits `voice_state_changed(False)`.

#### `cleanup_voice() -> None`
Stops the engine, cancels tasks, closes UDP transport, clears all state.

### Accessors

#### `get_room_code() -> str`
Returns the current room code from host or client.

---

## network.host — P2PHost

Server-side logic: accepts client connections, validates room codes, broadcasts messages, manages heartbeat.

### Methods

| Method                           | Description                                   |
|----------------------------------|-----------------------------------------------|
| `start(host_name, host_avatar)`  | Full session startup (SSL, server, voice)     |
| `stop()`                         | Clean shutdown + UPnP cleanup                 |
| `send_message(text, avatar, name)` | Send host message + broadcast                |
| `update_avatar(avatar)`          | Change host avatar + broadcast                |
| `_handle_client(reader, writer)` | Accept client, validate, send welcome         |
| `_client_read_loop(cid, reader)` | Read commands from a client                   |
| `_broadcast(data, exclude)`      | Send raw data to all clients except excluded  |
| `_background_setup()`            | Async IP fetch + UPnP port mapping            |
| `_heartbeat_loop()`              | Send `CMD_PING` every 45 seconds              |

---

## network.client — P2PClient

Client-side logic: connects to host, handles incoming commands, manages voice channel setup.

### Methods

| Method                                        | Description                              |
|-----------------------------------------------|------------------------------------------|
| `connect(host_ip, port, code, name, avatar)`  | TCP/SSL connect + HELLO → WELCOME        |
| `send_message(text, avatar, name)`            | Send message to host                     |
| `update_avatar(avatar)`                       | Send avatar change to host               |
| `disconnect()`                                | Voice cleanup + close writer             |
| `is_connected()`                              | Check if writer is active                |
| `_receive_loop(reader)`                       | Main receive loop (DIST_M, PAR_*, AVATAR, NAME, PING, VOICE_PORT) |

---

## network.protocol — P2PProtocol

Wire protocol using JSON + newline encoding.

### Commands

| Constant          | Value          | Direction        | Description                       |
|-------------------|----------------|------------------|-----------------------------------|
| `CMD_HELLO`       | `"HELLO"`      | Client → Host    | Handshake with room code          |
| `CMD_WELCOME`     | `"WELCOME"`    | Host → Client    | Participants + message history    |
| `CMD_SEND_M`      | `"SEND_M"`     | Client → Host    | Incoming message                  |
| `CMD_DIST_M`      | `"DIST_M"`     | Host → Clients   | Distribute message                |
| `CMD_PAR_JOIN`    | `"PAR_JOIN"`   | Host → Clients   | New participant joined            |
| `CMD_PAR_LEAVE`   | `"PAR_LEAVE"`  | Host → Clients   | Participant left                  |
| `CMD_AVATAR`      | `"AVATAR"`     | Bidirectional    | Avatar update                     |
| `CMD_NAME`        | `"NAME"`       | Host → Clients   | Name change                       |
| `CMD_VOICE_PORT`  | `"VOICE_PORT"` | Host → Client    | Voice UDP port announcement       |
| `CMD_VOICE_READY` | `"VOICE_READY"`| Client → Host    | Client voice port ready           |
| `CMD_PING`        | `"PING"`       | Host → Client    | Heartbeat (every 45s)             |

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
| `external_ip_ready`            | `(str)`                                 | External IP fetched asynchronously|
| `welcome_received`             | `(str, list, list)`                     | My name, participants, messages  |
| `message_received`             | `(str, str, str)`                       | Sender name, avatar, text        |
| `participant_joined`           | `(str, str)`                            | Name, avatar                     |
| `participant_left`             | `(str)`                                 | Name                             |
| `participant_avatar_updated`   | `(str, str)`                            | Name, new avatar                 |
| `participant_name_updated`     | `(str, str)`                            | Old name, new name               |
| `connection_failed`            | `(str)`                                 | Error message                    |
| `disconnected`                 | `()`                                    | Client disconnected              |
| `session_ended`                | `()`                                    | Server session ended             |
| `voice_state_changed`          | `(bool)`                                | Microphone active/inactive       |

---

## network.upnp — SessionCreator

Handles UPnP port forwarding, room code generation, and public IP discovery.

### Methods

| Method                        | Description                                   |
|-------------------------------|-----------------------------------------------|
| `get_room_code() -> str`      | Generates a random 7-character alphanumeric code |
| `get_host_ip() -> str`        | Returns public IP via `api.ipify.org` (timeout 3s, returns `""` on failure) |
| `get_host_ip_async() -> str`  | Async wrapper for `get_host_ip()`             |
| `find_local_port() -> int`    | Finds a free port in range 49152–65535        |
| `setup_upnp(port, protocol)`  | Async UPnP port mapping via executor          |
| `remove_port_mapping(port, protocol) -> bool` | Removes a UPnP port mapping      |

---

## network.models — Data Models

### `Message`
- `sender: str` — nickname
- `avatar: str` — base64 PNG
- `text: str` — message content

### `ClientConnection`
- `writer: StreamWriter`
- `reader: StreamReader`
- `name: str`
- `avatar: str`

---

## network.ssl_utils — SSL Utilities

Generates RSA-2048 keys and self-signed TLS certificates at runtime.

| Function                        | Description                                  |
|---------------------------------|----------------------------------------------|
| `generate_rsa_key(bits)`        | Creates an RSA private key                    |
| `generate_self_signed_cert(key)`| Returns `(cert_pem, key_pem)` bytes           |
| `create_server_ssl_context(cert, key)` | Creates `SSLContext` for TLS server     |
| `create_client_ssl_context()`   | Creates `SSLContext` for TLS client (no verification) |
| `init_rsa_key()`               | Starts background RSA key generation          |
| `get_rsa_key()`                 | Async getter that waits for key readiness     |
| `generate_session_certs()`      | Convenience: returns `(server_ctx, client_ctx)` |

---

## network.voice — VoiceEngine + JitterBuffer

Real-time audio capture/playback via `sounddevice` (PortAudio).

### `JitterBuffer`
Adaptive jitter buffer with sequence number tracking and packet loss concealment.

| Method                      | Description                        |
|-----------------------------|------------------------------------|
| `add(seq, payload)`         | Insert a packet by sequence number |
| `pop() -> bytes \| None`    | Retrieve next in-order packet      |
| `reset()`                   | Clear all state                    |

### `VoiceEngine`
Audio device abstraction with VAD (Voice Activity Detection).

| Attribute       | Value  | Description              |
|-----------------|--------|--------------------------|
| `SAMPLERATE`    | 16000  | Sample rate (Hz)         |
| `FRAME_SIZE`    | 320    | Frames per callback      |
| `CHANNELS`      | 1      | Mono                     |
| `VAD_THRESHOLD` | 500    | Silence threshold        |

| Method                             | Description                               |
|------------------------------------|-------------------------------------------|
| `start()`                          | Open and start input/output streams       |
| `stop()`                           | Stop and close streams, drain queues      |
| `get_encoded_frame() -> bytes`     | Blocking read from input queue            |
| `get_encoded_frame_nowait() -> bytes \| None` | Non-blocking read              |
| `put_pcm_frame(array)`             | Push PCM frame to output queue            |
| `put_pcm_bytes(data)`              | Push raw bytes (int16) to output queue    |
| `is_silence(frame, threshold)`     | Static VAD check                          |

---

## network.voice_protocol — VoiceProtocol

Binary protocol for UDP voice packets.

```
┌─────────┬──────────┬────────────┬──────────────┬──────────┐
│  Magic  │  Type    │  Sequence  │  Timestamp   │  Payload │
│ (2B LE) │  (1B)    │  (4B LE)   │  (8B LE)     │  (var)   │
└─────────┴──────────┴────────────┴──────────────┴──────────┘
```

| Constant      | Value  |
|---------------|--------|
| `MAGIC`       | `0xAD` |
| `HEADER_SIZE` | 15     |

| Method                     | Description                     |
|----------------------------|---------------------------------|
| `encode(payload, seq, ts)` | Pack header + payload → bytes   |
| `decode(data)`             | Unpack → `dict` with header fields + payload |

---

## network.voice_transport — VoiceTransport

UDP datagram transport using `asyncio.DatagramProtocol`.

| Method            | Description                    |
|-------------------|--------------------------------|
| `start()`         | Bind UDP socket on random port |
| `send(data, addr)`| Send packet to endpoint        |
| `close()`         | Close transport                |

---

## network.logger — Logger

Step-based logging to `log.txt` with timestamps and traceback support.

| Function                      | Description                          |
|-------------------------------|--------------------------------------|
| `clear()`                     | Truncate log file                    |
| `log(step, status, detail)`   | Write a log line + print to stderr   |
| `step_start(step, detail)`    | Log with `START` status              |
| `step_ok(step, detail)`       | Log with `OK` status                 |
| `step_fail(step, detail)`     | Log with `FAIL` status               |
| `step_exc(step, exc)`         | Log full traceback of an exception   |

---

## ui.main_window — MainWindow

Main application window built with PyQt5. Manages all UI elements and connects to `P2PManager` signals.

### Key UI Sections

- **Connect frame** — create/join session, room code display, clickable IP labels (global/LAN/local)
- **Join frame** — room code + IP:Port input for connecting
- **Members list** — online participants with avatars (updates on avatar/name change)
- **Chat display** — rendered HTML chat with right-aligned own messages, system messages in italic
- **Profile** — avatar selection (rounded), nickname input
- **Voice** — microphone toggle button (enabled only when in session)

### Key Callbacks

| Method                        | Trigger                               |
|-------------------------------|---------------------------------------|
| `_new_session()`              | "Создать сессию" button               |
| `_do_new_session()`           | Async handler for session creation    |
| `_connection()`               | "Подключиться" button (join frame)    |
| `_send_message()`             | Send button / Enter key               |
| `_end_session()`              | "Завершить сессию" button (host)      |
| `_disconnect()`               | "Отключиться" button (client)         |
| `_on_mic_toggled(checked)`   | Microphone toggle                     |

### Signal Slots

| Slot                          | Signal                                     |
|-------------------------------|--------------------------------------------|
| `_on_session_created`         | `P2PManager.signals.session_created`       |
| `_on_external_ip_ready`       | `P2PManager.signals.external_ip_ready`     |
| `_on_welcome_received`        | `P2PManager.signals.welcome_received`      |
| `_on_message_received`        | `P2PManager.signals.message_received`      |
| `_on_participant_joined`      | `P2PManager.signals.participant_joined`    |
| `_on_participant_left`        | `P2PManager.signals.participant_left`      |
| `_on_participant_avatar_updated` | `P2PManager.signals.participant_avatar_updated` |
| `_on_participant_name_updated`   | `P2PManager.signals.participant_name_updated` |
| `_on_connection_failed`       | `P2PManager.signals.connection_failed`     |
| `_on_disconnected`            | `P2PManager.signals.disconnected`          |
| `_on_session_ended`           | `P2PManager.signals.session_ended`         |
| `_on_voice_state_changed`     | `P2PManager.signals.voice_state_changed`   |

### UI Helpers

| Method                              | Description                               |
|-------------------------------------|-------------------------------------------|
| `_show_notification(text, duration)`| Center-screen toast notification          |
| `_copy_room_code()`                 | Copy room code to clipboard               |
| `_copy_global()`                    | Copy external IP:Port                     |
| `_copy_lan()`                       | Copy LAN IP:Port                          |
| `_copy_local()`                     | Copy localhost IP:Port                    |
| `_append_system_message(text)`      | Add italic system message to chat         |
| `_get_rounded_avatar(b64, size)`    | Cached round-corner avatar conversion     |
| `_render_chat()`                    | Full HTML re-render of chat history       |
| `_update_member_avatar(name, b64)`  | Update avatar in members list             |
| `_update_member_name(old, new)`     | Update name in members list               |
| `_update_chat_sender_names(old,new)`| Rewrite sender names in chat history      |

---

## utils.avatar — Avatar Utilities

Helper functions for avatar manipulation.

| Function                         | Description                               |
|----------------------------------|-------------------------------------------|
| `make_round_pixmap(pixmap, size)` | Crops a `QPixmap` into a circle           |
| `load_avatar_b64(file_path)`      | Reads an image file → base64 string       |
| `b64_to_pixmap(b64)`              | Decodes base64 → `QPixmap`               |
| `make_round_b64(b64, size)`       | Decodes, rounds, re-encodes to base64     |
| `set_round_pixmap_on_label(...)`  | Sets a rounded pixmap on a `QLabel`      |
| `load_from_file_and_display(...)` | Loads file → displays on label → returns base64 |
| `select_avatar(parent, label)`    | Opens file dialog → returns base64       |
| `load_default_avatar(label)`      | Loads `resources/account.png` (supports PyInstaller) |
