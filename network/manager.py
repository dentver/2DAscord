from .signals import P2PSignals
from .host import P2PHost
from .client import P2PClient
from .voice_controller import VoiceController
from .logger import step_start, step_ok, step_fail


class P2PManager:
    signals = P2PSignals()
    _voice = VoiceController(signals)
    _host = P2PHost(signals, _voice)
    _client = P2PClient(signals, _voice)

    # ── Host ─────────────────────────────────────────────

    @classmethod
    async def start_server(cls, host_name: str, host_avatar: str) -> None:
        step_start("MGR_START", f"name={host_name}")
        try:
            await cls._host.start(host_name, host_avatar)
            step_ok("MGR_START", "host.start returned")
        except Exception as e:
            step_fail("MGR_START", str(e))
            raise

    @classmethod
    async def host_send_message(cls, text: str, avatar: str = "", name: str = "") -> None:
        await cls._host.send_message(text, avatar, name)

    @classmethod
    async def host_update_avatar(cls, avatar: str) -> None:
        await cls._host.update_avatar(avatar)

    @classmethod
    async def stop_server(cls) -> None:
        await cls._host.stop()

    # ── Client ───────────────────────────────────────────

    @classmethod
    async def connect(
        cls, host_ip: str, host_port: int, room_code: str,
        name: str, avatar: str
    ) -> None:
        await cls._client.connect(host_ip, host_port, room_code, name, avatar)

    @classmethod
    async def client_send_message(cls, text: str, avatar: str = "", name: str = "") -> None:
        await cls._client.send_message(text, avatar, name)

    @classmethod
    async def client_update_avatar(cls, avatar: str) -> None:
        await cls._client.update_avatar(avatar)

    @classmethod
    async def disconnect(cls) -> None:
        await cls._client.disconnect()

    # ── Voice ────────────────────────────────────────────

    @classmethod
    async def enable_voice(cls) -> None:
        await cls._voice.enable()

    @classmethod
    async def disable_voice(cls) -> None:
        await cls._voice.disable()

    @classmethod
    async def cleanup_voice(cls) -> None:
        await cls._voice.cleanup()

    # ── Accessors ─────────────────────────────────────────

    @classmethod
    def is_connected(cls) -> bool:
        return cls._client.is_connected()

    @classmethod
    def get_room_code(cls) -> str:
        return cls._host.room_code or cls._client.room_code
