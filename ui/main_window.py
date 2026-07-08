import asyncio
import logging
from pathlib import Path
from getpass import getuser

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget, QDialogButtonBox, QFormLayout
)

from network.manager import P2PManager
from utils.avatar import (
    select_avatar, load_default_avatar, b64_to_pixmap, make_round_pixmap
)

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._avatar_b64 = ""
        self._is_host = False

        self.setWindowTitle("2DAscord")
        self.setWindowIcon(QIcon(str(Path("resources") / "2DAicon.png")))
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # ── Левая панель ──────────────────────────────────
        left_panel = QWidget()
        left_panel.setObjectName("leftPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 10, 10, 10)
        left_layout.setSpacing(12)

        # Подключение
        connect_frame = QFrame()
        connect_frame.setObjectName("card")

        self.join_frame = QFrame()
        self.join_frame.setObjectName("card")
        self.join_frame.setVisible(False)
        join_layout = QVBoxLayout(self.join_frame)

        join_title = QLabel("Параметры подключения")
        join_title.setObjectName("sectionTitle")
        join_layout.addWidget(join_title)

        form_layout = QFormLayout()
        self.join_ip_input = QLineEdit()
        self.join_ip_input.setPlaceholderText("например, 83.234.21.109")
        form_layout.addRow("IP-адрес хоста:", self.join_ip_input)

        self.join_port_input = QLineEdit()
        self.join_port_input.setPlaceholderText("например, 51820")
        form_layout.addRow("Порт:", self.join_port_input)

        self.join_code_input = QLineEdit()
        self.join_code_input.setPlaceholderText("например, A3fG9k")
        form_layout.addRow("Код сессии:", self.join_code_input)

        join_layout.addLayout(form_layout)

        button_box = QDialogButtonBox()
        self.join_connect_btn = button_box.addButton("Подключиться", QDialogButtonBox.AcceptRole)
        self.join_cancel_btn = button_box.addButton("Закрыть", QDialogButtonBox.RejectRole)
        join_layout.addWidget(button_box)

        self.join_cancel_btn.clicked.connect(self._hide_join_frame)
        self.join_connect_btn.clicked.connect(self._connection)

        left_layout.addWidget(self.join_frame)

        connect_layout = QVBoxLayout(connect_frame)
        connect_title = QLabel("Подключение")
        connect_title.setObjectName("sectionTitle")
        self.session_key_label = QLabel("Код сессии: не создана")
        self.status_label = QLabel("Статус: ожидание")
        self.create_session_btn = QPushButton("Создать сессию")
        self.join_session_btn = QPushButton("Подключиться")
        self.join_session_btn.clicked.connect(self._show_join_frame)
        self.create_session_btn.clicked.connect(self._new_session)

        connect_layout.addWidget(connect_title)
        connect_layout.addWidget(self.session_key_label)
        connect_layout.addWidget(self.status_label)
        self.end_session_btn = QPushButton("Завершить сессию")
        self.end_session_btn.setVisible(False)
        self.end_session_btn.setStyleSheet("background-color: #da373c; color: white;")
        self.end_session_btn.clicked.connect(self._end_session)

        connect_layout.addWidget(self.create_session_btn)
        connect_layout.addWidget(self.join_session_btn)
        connect_layout.addWidget(self.end_session_btn)

        # Участники
        members_frame = QFrame()
        members_frame.setObjectName("card")
        members_layout = QVBoxLayout(members_frame)
        self.members_title = QLabel("Участники (0)")
        self.members_title.setObjectName("sectionTitle")
        self.members_list = QListWidget()
        members_layout.addWidget(self.members_title)
        members_layout.addWidget(self.members_list)

        # Медиа
        media_frame = QFrame()
        media_frame.setObjectName("card")
        media_layout = QVBoxLayout(media_frame)
        media_title = QLabel("Голосовая связь")
        media_title.setObjectName("sectionTitle")
        self.mic_btn = QPushButton("Микрофон")
        self.screen_btn = QPushButton("Демонстрация")
        self.mic_btn.setCheckable(True)
        self.screen_btn.setCheckable(True)
        media_layout.addWidget(media_title)
        media_layout.addWidget(self.mic_btn)
        media_layout.addWidget(self.screen_btn)

        # Профиль
        profile_frame = QFrame()
        profile_frame.setObjectName("card")
        profile_layout = QVBoxLayout(profile_frame)
        profile_title = QLabel("Профиль")
        profile_title.setObjectName("sectionTitle")
        profile_layout.addWidget(profile_title)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setObjectName("avatarPreview")
        self.avatar_label.setScaledContents(False)

        self.avatar_btn = QPushButton("Выбрать аватар")
        self.avatar_btn.clicked.connect(self._select_avatar_clicked)

        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("Введите никнейм")
        self.nickname_input.setText(getuser())

        profile_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        profile_layout.addWidget(self.avatar_btn)
        profile_layout.addWidget(self.nickname_input)

        left_layout.addWidget(connect_frame)
        left_layout.addWidget(members_frame)
        left_layout.addWidget(media_frame)
        left_layout.addWidget(profile_frame)
        left_layout.addStretch()

        # ── Правая панель ─────────────────────────────────
        right_panel = QWidget()
        right_panel.setObjectName("rightPanel")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(15, 15, 15, 15)
        right_layout.setSpacing(10)

        chat_title = QLabel("# общий-чат")
        chat_title.setObjectName("sectionTitle")
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        self.chat_display.setPlaceholderText("История сообщений...")

        input_layout = QHBoxLayout()
        self.message_input = QLineEdit()
        self.message_input.setPlaceholderText("Введите сообщение...")
        self.send_btn = QPushButton("Отправить")
        input_layout.addWidget(self.message_input)
        input_layout.addWidget(self.send_btn)

        right_layout.addWidget(chat_title)
        right_layout.addWidget(self.chat_display)
        right_layout.addLayout(input_layout)

        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([320, 1000])

        main_layout.addWidget(splitter)

        self._load_styles()
        self._avatar_b64 = load_default_avatar(self.avatar_label)

        # ── Сигналы P2P ───────────────────────────────────
        P2PManager.signals.session_created.connect(self._on_session_created)
        P2PManager.signals.welcome_received.connect(self._on_welcome_received)
        P2PManager.signals.message_received.connect(self._on_message_received)
        P2PManager.signals.participant_joined.connect(self._on_participant_joined)
        P2PManager.signals.participant_left.connect(self._on_participant_left)
        P2PManager.signals.connection_failed.connect(self._on_connection_failed)
        P2PManager.signals.disconnected.connect(self._on_disconnected)
        P2PManager.signals.session_ended.connect(self._on_session_ended)

        # ── Кнопка отправки ───────────────────────────────
        self.send_btn.clicked.connect(self._send_message)
        self.message_input.returnPressed.connect(self._send_message)

    # ── Стили ────────────────────────────────────────────

    def _load_styles(self) -> None:
        css_path = Path("resources") / "main.css"
        try:
            self.setStyleSheet(css_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            logger.warning("main.css не найден")

    # ── Фрейм подключения ────────────────────────────────

    def _show_join_frame(self) -> None:
        self.join_ip_input.clear()
        self.join_port_input.clear()
        self.join_code_input.clear()
        self.join_frame.setVisible(True)

    def _hide_join_frame(self) -> None:
        self.join_frame.setVisible(False)

    # ── Аватар ───────────────────────────────────────────

    def _select_avatar_clicked(self) -> None:
        result = select_avatar(self, self.avatar_label)
        if result:
            self._avatar_b64 = result

    # ── P2P ──────────────────────────────────────────────

    def _new_session(self) -> None:
        self.create_session_btn.setVisible(False)
        self.join_session_btn.setVisible(False)
        self.end_session_btn.setVisible(True)
        self._is_host = True
        name = self.nickname_input.text().strip() or getuser()
        asyncio.create_task(P2PManager.start_server(name, self._avatar_b64))

    def _connection(self) -> None:
        ip = self.join_ip_input.text().strip()
        port_str = self.join_port_input.text().strip()
        code = self.join_code_input.text().strip()
        name = self.nickname_input.text().strip() or getuser()
        if not ip or not port_str or not code:
            return
        port = int(port_str)
        self._hide_join_frame()
        self._is_host = False
        self.status_label.setText("Статус: подключение...")
        asyncio.create_task(
            P2PManager.connect(ip, port, code, name, self._avatar_b64)
        )

    def _send_message(self) -> None:
        text = self.message_input.text().strip()
        if not text:
            return
        self.message_input.clear()
        if self._is_host:
            asyncio.create_task(P2PManager.host_send_message(text))
        else:
            asyncio.create_task(P2PManager.client_send_message(text))

    def _end_session(self) -> None:
        asyncio.create_task(self._do_end_session())

    async def _do_end_session(self) -> None:
        await P2PManager.stop_server()

    # ── Слоты сигналов ───────────────────────────────────

    def _on_session_created(self, room_code: str, host_ip: str, port: int) -> None:
        self.session_key_label.setText(f"Код сессии: {room_code}")
        self.status_label.setText(f"Статус: хост ({host_ip}:{port})")
        self._add_member(
            self.nickname_input.text().strip() or getuser(),
            self._avatar_b64
        )

    def _on_welcome_received(self, my_name: str, participants: list, messages: list) -> None:
        self.status_label.setText(f"Статус: подключен как {my_name}")
        self.members_list.clear()
        for p in participants:
            self._add_member(p["name"], p["avatar"])
        self.chat_display.clear()
        for m in messages:
            self._append_message(m["sender"], m["avatar"], m["text"])

    def _on_message_received(self, sender: str, avatar_b64: str, text: str) -> None:
        self._append_message(sender, avatar_b64, text)

    def _on_participant_joined(self, name: str, avatar_b64: str) -> None:
        self._add_member(name, avatar_b64)

    def _on_participant_left(self, name: str) -> None:
        for i in range(self.members_list.count()):
            item = self.members_list.item(i)
            widget = self.members_list.itemWidget(item)
            if widget and widget.property("name") == name:
                self.members_list.takeItem(i)
                break
        self._update_members_count()

    def _on_connection_failed(self, error: str) -> None:
        self.status_label.setText(f"Статус: ошибка — {error}")

    def _on_disconnected(self) -> None:
        self.status_label.setText("Статус: отключён")

    def _on_session_ended(self) -> None:
        self.create_session_btn.setVisible(True)
        self.join_session_btn.setVisible(True)
        self.end_session_btn.setVisible(False)
        self._is_host = False
        self.session_key_label.setText("Код сессии: не создана")
        self.status_label.setText("Статус: ожидание")
        self.members_list.clear()
        self.members_title.setText("Участники (0)")
        self.chat_display.clear()

    # ── UI helpers ───────────────────────────────────────

    def _append_message(self, sender: str, avatar_b64: str, text: str) -> None:
        html = '<div style="display: flex; align-items: flex-start; margin: 4px 0;">'
        if avatar_b64:
            html += (
                '<img src="data:image/png;base64,{}" '
                'width="32" height="32" '
                'style="border-radius: 16px; margin-right: 8px; flex-shrink: 0;">'
            ).format(avatar_b64)
        html += (
            '<div><b style="color: #dbdee1;">{}</b>'
            '<span style="color: #dbdee1;"> {}</span></div>'
            '</div>'
        ).format(sender, text)
        self.chat_display.insertHtml(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_member(self, name: str, avatar_b64: str) -> None:
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        avatar_label = QLabel()
        avatar_label.setFixedSize(32, 32)
        if avatar_b64:
            pixmap = b64_to_pixmap(avatar_b64)
            round_pixmap = make_round_pixmap(pixmap, 32)
            avatar_label.setPixmap(round_pixmap)

        name_label = QLabel(name)
        name_label.setStyleSheet("color: #dbdee1;")

        layout.addWidget(avatar_label)
        layout.addWidget(name_label)
        layout.addStretch()

        widget.setProperty("name", name)
        item.setSizeHint(widget.sizeHint())
        self.members_list.addItem(item)
        self.members_list.setItemWidget(item, widget)
        self._update_members_count()

    def _update_members_count(self) -> None:
        count = self.members_list.count()
        self.members_title.setText(f"Участники ({count})")
