from PyQt5.QtCore import QObject, pyqtSignal


# ── Сигналы P2P ─────────────────────────────────────────


class P2PSignals(QObject):
    session_created = pyqtSignal(str, str, int)
    external_ip_ready = pyqtSignal(str)
    welcome_received = pyqtSignal(str, list, list)
    message_received = pyqtSignal(str, str, str)
    participant_joined = pyqtSignal(str, str)
    participant_left = pyqtSignal(str)
    participant_avatar_updated = pyqtSignal(str, str)
    participant_name_updated = pyqtSignal(str, str)
    connection_failed = pyqtSignal(str)
    disconnected = pyqtSignal()
    session_ended = pyqtSignal()
    voice_state_changed = pyqtSignal(bool)
