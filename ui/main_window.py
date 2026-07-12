import asyncio
import sys
from pathlib import Path
from getpass import getuser

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QIcon, QCursor
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMainWindow, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget, QDialogButtonBox, QFormLayout
)

from network.manager import P2PManager
from utils.avatar import (
    select_avatar, load_default_avatar, b64_to_pixmap, make_round_pixmap,
    make_round_b64
)


class ClickableLabel(QLabel):
    clicked = pyqtSignal()

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setObjectName("copyLabel")

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._avatar_b64 = ""
        self._my_name = ""
        self._is_host = False
        self._host_address = ""
        self._room_code = ""
        self._chat_messages: list = []

        self.setWindowTitle("2DAscord")
        if getattr(sys, 'frozen', False):
            icon_path = str(Path(sys._MEIPASS) / "resources" / "2DAicon.png")
        else:
            icon_path = str(Path("resources") / "2DAicon.png")
        self.setWindowIcon(QIcon(icon_path))
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
        self.connect_frame = connect_frame

        self.join_frame = QFrame()
        self.join_frame.setObjectName("card")
        self.join_frame.setVisible(False)
        join_layout = QVBoxLayout(self.join_frame)

        join_title = QLabel("Параметры подключения")
        join_title.setObjectName("sectionTitle")
        join_layout.addWidget(join_title)

        join_code_input = QLineEdit()
        join_code_input.setPlaceholderText("Код сессии")
        self.join_code_input = join_code_input
        join_layout.addWidget(join_code_input)

        join_input = QLineEdit()
        join_input.setPlaceholderText("IP:Port")
        self.join_input = join_input
        join_layout.addWidget(join_input)

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
        self.session_key_label = ClickableLabel("Код сессии: не создана")
        self.status_label = QLabel("Статус: нет активной сессии")
        self.create_session_btn = QPushButton("Создать сессию")
        self.join_session_btn = QPushButton("Подключиться")
        self.join_session_btn.clicked.connect(self._show_join_frame)
        self.create_session_btn.clicked.connect(self._new_session)
        self.disconnect_btn = QPushButton("Отключиться")
        self.disconnect_btn.setVisible(False)
        self.disconnect_btn.setStyleSheet("background-color: #da373c; color: white;")
        self.disconnect_btn.clicked.connect(self._disconnect)

        connect_layout.addWidget(connect_title)
        connect_layout.addWidget(self.session_key_label)
        self.host_global_label = ClickableLabel()
        self.host_global_label.setVisible(False)
        self.host_lan_label = ClickableLabel()
        self.host_lan_label.setVisible(False)
        self.host_local_label = ClickableLabel()
        self.host_local_label.setVisible(False)
        connect_layout.addWidget(self.host_global_label)
        connect_layout.addWidget(self.host_lan_label)
        connect_layout.addWidget(self.host_local_label)
        connect_layout.addWidget(self.status_label)
        self.end_session_btn = QPushButton("Завершить сессию")
        self.end_session_btn.setVisible(False)
        self.end_session_btn.setStyleSheet("background-color: #da373c; color: white;")
        self.end_session_btn.clicked.connect(self._end_session)

        connect_layout.addWidget(self.create_session_btn)
        connect_layout.addWidget(self.join_session_btn)
        connect_layout.addWidget(self.disconnect_btn)
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

        # ── Уведомление ───────────────────────────────────
        self.notification_label = QLabel(self)
        self.notification_label.setObjectName("notificationLabel")
        self.notification_label.setVisible(False)
        self.notification_label.setAlignment(Qt.AlignCenter)
        self.notification_timer = QTimer(self)
        self.notification_timer.setSingleShot(True)
        self.notification_timer.timeout.connect(lambda: self.notification_label.setVisible(False))

        # ── Сигналы P2P ───────────────────────────────────
        P2PManager.signals.session_created.connect(self._on_session_created)
        P2PManager.signals.welcome_received.connect(self._on_welcome_received)
        P2PManager.signals.participant_avatar_updated.connect(self._on_participant_avatar_updated)
        P2PManager.signals.participant_name_updated.connect(self._on_participant_name_updated)
        P2PManager.signals.participant_joined.connect(self._on_participant_joined)
        P2PManager.signals.participant_left.connect(self._on_participant_left)
        P2PManager.signals.message_received.connect(self._on_message_received)
        P2PManager.signals.connection_failed.connect(self._on_connection_failed)
        P2PManager.signals.disconnected.connect(self._on_disconnected)
        P2PManager.signals.session_ended.connect(self._on_session_ended)

        # ── Копирование ───────────────────────────
        self.session_key_label.clicked.connect(self._copy_room_code)
        self.host_global_label.clicked.connect(self._copy_global)
        self.host_lan_label.clicked.connect(self._copy_lan)
        self.host_local_label.clicked.connect(self._copy_local)

        # ── Кнопка отправки ───────────────────────────────
        self.send_btn.clicked.connect(self._send_message)
        self.message_input.returnPressed.connect(self._send_message)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.notification_label.isVisible():
            self.notification_label.adjustSize()
            x = (self.width() - self.notification_label.width()) // 2
            y = self.height() // 2
            self.notification_label.move(x, y)

    def _show_notification(self, text: str, duration: int = 3000):
        self.notification_label.setText(text)
        self.notification_label.adjustSize()
        x = (self.width() - self.notification_label.width()) // 2
        y = self.height() // 2
        self.notification_label.move(x, y)
        self.notification_label.setVisible(True)
        self.notification_label.raise_()
        self.notification_timer.start(duration)

    # ── Копирование ──────────────────────────────────────

    def _copy_room_code(self):
        if self._room_code:
            self._copy_to_clipboard(self._room_code)
            self._show_notification("Код скопирован")

    def _copy_global(self):
        self._copy_to_clipboard(self._host_global)

    def _copy_lan(self):
        self._copy_to_clipboard(self._host_lan)

    def _copy_local(self):
        self._copy_to_clipboard(self._host_local)

    def _copy_to_clipboard(self, text: str):
        QApplication.clipboard().setText(text)

    # ── Стили ────────────────────────────────────────────

    def _load_styles(self) -> None:
        if getattr(sys, 'frozen', False):
            base = Path(sys._MEIPASS)
        else:
            base = Path.cwd()
        css_path = base / "resources" / "main.css"
        try:
            self.setStyleSheet(css_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            pass

    # ── Фрейм подключения ────────────────────────────────

    def _show_join_frame(self) -> None:
        self.join_frame.setVisible(True)
        self.connect_frame.setVisible(False)

    def _hide_join_frame(self) -> None:
        self.join_frame.setVisible(False)
        self.connect_frame.setVisible(True)

    # ── Аватар ───────────────────────────────────────────

    def _select_avatar_clicked(self) -> None:
        result = select_avatar(self, self.avatar_label)
        if result:
            self._avatar_b64 = result
            if self._is_host:
                asyncio.create_task(P2PManager.host_update_avatar(result))
            elif P2PManager._client_writer:
                asyncio.create_task(P2PManager.client_update_avatar(result))

    # ── P2P ──────────────────────────────────────────────

    def _new_session(self) -> None:
        self.create_session_btn.setVisible(False)
        self.join_session_btn.setVisible(False)
        self.end_session_btn.setVisible(True)
        self._is_host = True
        self._my_name = self.nickname_input.text().strip() or getuser()
        asyncio.create_task(P2PManager.start_server(self._my_name, self._avatar_b64))

    def _connection(self) -> None:
        raw = self.join_input.text().strip()
        code = self.join_code_input.text().strip()
        name = self.nickname_input.text().strip() or getuser()
        if not raw:
            self.status_label.setText("Статус: неверный формат IP/Port")
            return
        self._room_code = code
        self.join_connect_btn.setEnabled(False)
        self.join_connect_btn.setText("Подключение...")
        self._is_host = False
        self.status_label.setText("Статус: подключение...")
        try:
            port_sep = raw.rindex(":")
            host_part = raw[:port_sep]
            port_str = raw[port_sep + 1:]
            ip = host_part
            port = int(port_str)
        except (ValueError, IndexError):
            self.status_label.setText("Статус: неверный формат IP/Port")
            return
        asyncio.create_task(
            P2PManager.connect(ip, port, code, name, self._avatar_b64)
        )

    def _send_message(self) -> None:
        text = self.message_input.text().strip()
        if not text:
            return
        self.message_input.clear()
        avatar = self._avatar_b64
        name = self.nickname_input.text().strip() or getuser()
        if self._is_host:
            asyncio.create_task(P2PManager.host_send_message(text, avatar, name))
        else:
            asyncio.create_task(P2PManager.client_send_message(text, avatar, name))

    def _end_session(self) -> None:
        asyncio.create_task(self._do_end_session())

    async def _do_end_session(self) -> None:
        await P2PManager.stop_server()

    def _disconnect(self) -> None:
        asyncio.create_task(self._do_disconnect())

    async def _do_disconnect(self) -> None:
        await P2PManager.disconnect()

    # ── Слоты сигналов ───────────────────────────────────

    def _get_lan_ip(self) -> str:
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _on_session_created(self, room_code: str, host_ip: str, port: int) -> None:
        self.session_key_label.setText(f"Код сессии: {room_code}")
        self._room_code = room_code
        lam_ip = self._get_lan_ip()
        self._host_global = f"{host_ip}:{port}"
        self._host_lan = f"{lam_ip}:{port}"
        self._host_local = f"127.0.0.1:{port}"
        self.host_global_label.setText(f"внешний: {self._host_global}")
        self.host_lan_label.setText(f"LAN: {self._host_lan}")
        self.host_local_label.setText(f"локальный: {self._host_local}")
        self.host_global_label.setVisible(True)
        self.host_lan_label.setVisible(True)
        self.host_local_label.setVisible(True)
        self.status_label.setText("Статус: сессия активна")
        self._add_member(
            self.nickname_input.text().strip() or getuser(),
            self._avatar_b64
        )

    def _on_welcome_received(self, my_name: str, participants: list, messages: list) -> None:
        self._my_name = my_name
        self._room_code = P2PManager._room_code or self._room_code
        self.session_key_label.setText(f"Код сессии: {self._room_code}")
        self.status_label.setText("Статус: подключение выполнено")
        self._hide_join_frame()
        self.create_session_btn.setVisible(False)
        self.join_session_btn.setVisible(False)
        self.disconnect_btn.setVisible(True)
        self.members_list.clear()
        for p in participants:
            self._add_member(p["name"], p["avatar"])
        self._chat_messages = [(m["sender"], m["avatar"], m["text"]) for m in messages]
        self._render_chat()

    def _on_message_received(self, sender: str, avatar_b64: str, text: str) -> None:
        self._append_message(sender, avatar_b64, text)
        if avatar_b64:
            self._update_member_avatar(sender, avatar_b64)

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
        self._append_system_message(f"участник {name} покинул сессию")

    def _on_participant_avatar_updated(self, name: str, avatar_b64: str) -> None:
        pass

    def _on_participant_name_updated(self, old_name: str, new_name: str) -> None:
        self._update_chat_sender_names(old_name, new_name)
        self._update_member_name(old_name, new_name)
        if self._my_name == old_name:
            self._my_name = new_name

    def _on_connection_failed(self, error: str) -> None:
        self.join_connect_btn.setEnabled(True)
        self.join_connect_btn.setText("Подключиться")
        self.status_label.setText("Статус: не удалось подключиться")
        self._room_code = self.join_code_input.text().strip() or self._room_code
        self._show_notification(f"Ошибка подключения: {error}", 5000)

    def _on_disconnected(self) -> None:
        if not self._is_host:
            self._on_session_ended()
        else:
            self.status_label.setText("Статус: нет активной сессии")

    def _on_session_ended(self) -> None:
        self.create_session_btn.setVisible(True)
        self.join_session_btn.setVisible(True)
        self.end_session_btn.setVisible(False)
        self.disconnect_btn.setVisible(False)
        self._is_host = False
        self._my_name = ""
        self._chat_messages.clear()
        self.session_key_label.setText("Код сессии: не создана")
        self.status_label.setText("Статус: нет активной сессии")
        self.members_list.clear()
        self.members_title.setText("Участники (0)")
        self.chat_display.clear()
        self.host_global_label.setVisible(False)
        self.host_lan_label.setVisible(False)
        self.host_local_label.setVisible(False)
        self._show_notification("Сессия завершена")

    # ── UI helpers ───────────────────────────────────────

    def _append_message(self, sender: str, avatar_b64: str, text: str) -> None:
        for i, (s, a, t) in enumerate(self._chat_messages):
            if s == sender:
                self._chat_messages[i] = (s, avatar_b64, t)
        self._chat_messages.append((sender, avatar_b64, text))
        self._render_chat()

    def _append_system_message(self, text: str) -> None:
        self._append_message("", "", text)

    def _render_chat(self) -> None:
        parts = []
        for sender, avatar_b64, text in self._chat_messages:
            is_system = not sender and not avatar_b64
            is_mine = sender == self._my_name

            if is_system:
                msg = (
                    '<p style="padding: 2px 0; margin: 0; text-align: center; '
                    'font-style: italic; color: #888;">{}</p>'
                ).format(text)
                parts.append(msg)
                continue

            msg = '<p style="padding: 2px 0; margin: 0; text-align: {};">'.format(
                "right" if is_mine else "left"
            )

            if not is_mine:
                if avatar_b64:
                    round_b64 = make_round_b64(avatar_b64, 32)
                    msg += (
                        '<img src="data:image/png;base64,{}" '
                        'width="32" height="32" '
                        'style="border-radius: 16px; margin-right: 8px; vertical-align: middle;">'
                    ).format(round_b64)
                msg += (
                    '<b style="color: #dbdee1;">{}</b>'
                    '<span style="color: #dbdee1;"> {}</span>'
                ).format(sender, text)
            else:
                msg += (
                    '<b style="color: #dbdee1;">{}</b>'
                    '<span style="color: #dbdee1;"> {}</span>'
                ).format(sender, text)
                if avatar_b64:
                    round_b64 = make_round_b64(avatar_b64, 32)
                    msg += (
                        '<img src="data:image/png;base64,{}" '
                        'width="32" height="32" '
                        'style="border-radius: 16px; margin-left: 8px; vertical-align: middle;">'
                    ).format(round_b64)

            msg += "</p>"
            parts.append(msg)

        html = (
            '<html><body style="background-color: transparent; margin: 0; padding: 0;">'
            '{}'
            '</body></html>'
        ).format("".join(parts))

        self.chat_display.setHtml(html)
        scrollbar = self.chat_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _add_member(self, name: str, avatar_b64: str) -> None:
        item = QListWidgetItem()
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        avatar_label = QLabel()
        avatar_label.setObjectName("memberAvatar")
        avatar_label.setFixedSize(32, 32)
        if avatar_b64:
            pixmap = b64_to_pixmap(avatar_b64)
            round_pixmap = make_round_pixmap(pixmap, 32)
            avatar_label.setPixmap(round_pixmap)

        name_label = QLabel(name)
        name_label.setObjectName("memberName")
        name_label.setStyleSheet("color: #dbdee1;")

        layout.addWidget(avatar_label)
        layout.addWidget(name_label)
        layout.addStretch()

        widget.setProperty("name", name)
        item.setSizeHint(widget.sizeHint())
        self.members_list.addItem(item)
        self.members_list.setItemWidget(item, widget)
        self._update_members_count()

    def _update_member_avatar(self, name: str, avatar_b64: str) -> None:
        for i in range(self.members_list.count()):
            item = self.members_list.item(i)
            widget = self.members_list.itemWidget(item)
            if widget and widget.property("name") == name:
                pixmap = b64_to_pixmap(avatar_b64)
                round_pixmap = make_round_pixmap(pixmap, 32)
                avatar_label = widget.findChild(QLabel, "memberAvatar")
                if avatar_label:
                    avatar_label.setPixmap(round_pixmap)
                break

    def _update_member_name(self, old_name: str, new_name: str) -> None:
        for i in range(self.members_list.count()):
            item = self.members_list.item(i)
            widget = self.members_list.itemWidget(item)
            if widget and widget.property("name") == old_name:
                widget.setProperty("name", new_name)
                name_label = widget.findChild(QLabel, "memberName")
                if name_label:
                    name_label.setText(new_name)
                break

    def _update_chat_sender_names(self, old_name: str, new_name: str) -> None:
        for i, (s, a, t) in enumerate(self._chat_messages):
            if s == old_name:
                self._chat_messages[i] = (new_name, a, t)
        self._render_chat()

    def _update_members_count(self) -> None:
        count = self.members_list.count()
        self.members_title.setText(f"Участники ({count})")
