from PyQt5.QtCore import QObject, pyqtSignal


class P2PSignals(QObject):
    session_created = pyqtSignal(str, str, int)
    welcome_received = pyqtSignal(str, list, list)
    message_received = pyqtSignal(str, str, str)
    participant_joined = pyqtSignal(str, str)
    participant_left = pyqtSignal(str)
    connection_failed = pyqtSignal(str)
    disconnected = pyqtSignal()
    session_ended = pyqtSignal()
