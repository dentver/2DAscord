import sys
import os
import PyQt5
from getpass import getuser
from PIL import Image
from os.path import expanduser
from p2p_manager import p2pManager

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QBrush, QImage
from PyQt5.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QMainWindow, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget, QFileDialog, QDialogButtonBox, QFormLayout
)

qt_plugin_path = os.path.join(os.path.dirname(PyQt5.__file__), 'Qt5', 'plugins', 'platforms')
os.environ['QT_QPA_PLATFORM_PLUGIN_PATH'] = qt_plugin_path


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("2DAscord")
        self.setWindowIcon(QIcon("resources/2DAicon.png"))
        self.resize(1400, 900)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)

        # =================================
        # ЛЕВАЯ ПАНЕЛЬ
        # =================================
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
        self.join_frame.setVisible(False)   # изначально скрыт
        join_layout = QVBoxLayout(self.join_frame)

        # Заголовок фрейма
        join_title = QLabel("Параметры подключения")
        join_title.setObjectName("sectionTitle")
        join_layout.addWidget(join_title)

        # Форма с полями
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

        # Кнопки: Подключиться и Закрыть
        button_box = QDialogButtonBox()
        self.join_connect_btn = button_box.addButton("Подключиться", QDialogButtonBox.AcceptRole)
        self.join_cancel_btn = button_box.addButton("Закрыть", QDialogButtonBox.RejectRole)
        join_layout.addWidget(button_box)

        # Сигналы кнопок
        self.join_cancel_btn.clicked.connect(self.hide_join_frame)
        self.join_connect_btn.clicked.connect(self.connection)

        left_layout.addWidget(self.join_frame)
        connect_layout = QVBoxLayout(connect_frame)
        connect_title = QLabel("Подключение")
        connect_title.setObjectName("sectionTitle")
        self.session_key_label = QLabel("Код сессии: не создана")
        self.status_label = QLabel("Статус: ожидание")
        self.create_session_btn = QPushButton("Создать сессию")
        self.join_session_btn = QPushButton("Подключиться")
        self.join_session_btn.clicked.connect(self.show_join_frame)
        self.create_session_btn.clicked.connect(self.new_session)
        
        connect_layout.addWidget(connect_title)
        connect_layout.addWidget(self.session_key_label)
        connect_layout.addWidget(self.status_label)
        connect_layout.addWidget(self.create_session_btn)
        connect_layout.addWidget(self.join_session_btn)

        # Участники
        members_frame = QFrame()
        members_frame.setObjectName("card")
        members_layout = QVBoxLayout(members_frame)
        members_title = QLabel("Участники (0)")
        members_title.setObjectName("sectionTitle")
        self.members_list = QListWidget()
        members_layout.addWidget(members_title)
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

        # Аватарка
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setObjectName("avatarPreview")
        self.avatar_label.setScaledContents(False)

        self.avatar_btn = QPushButton("Выбрать аватар")
        self.avatar_btn.clicked.connect(self.select_avatar)

        # Никнейм
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

        # =================================
        # ПРАВАЯ ПАНЕЛЬ
        # =================================
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

        self.load_styles()
        self.load_default_avatar()   # загружаем аватар по умолчанию

    # ---------- НОВЫЕ МЕТОДЫ ДЛЯ РАБОТЫ С КРУГЛОЙ АВАТАРКОЙ ----------
    def make_round_pixmap(self, pixmap, size=75):
        """Преобразует любой QPixmap в круглый размера size x size."""
        if pixmap.isNull():
            return pixmap
        # Масштабируем с обрезанием до квадрата size x size
        scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        # Создаём прозрачный холст
        round_pixmap = QPixmap(size, size)
        round_pixmap.fill(Qt.transparent)
        painter = QPainter(round_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(QBrush(scaled))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(0, 0, size, size)
        painter.end()
        return round_pixmap

    def load_avatar_from_file(self, file_path):
        file_path = os.path.abspath(file_path)

        target_size = 75
        pixmap = None

        with Image.open(file_path) as pil_image:
                    # Конвертируем в RGB, если нужно (например, CMYK -> RGB)
                    if pil_image.mode not in ('RGB', 'RGBA'):
                        pil_image = pil_image.convert('RGB')
                    # Уменьшаем до разумного размера (400px) для экономии памяти
                    pil_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
                    # Преобразуем PIL Image в QImage
                    if pil_image.mode == 'RGB':
                        pil_image = pil_image.convert('RGBA')
                    data = pil_image.tobytes('raw', 'RGBA')
                    qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(qimage)

        # Масштабируем до 80x80 с обрезанием и делаем круглым
        final_pixmap = pixmap.scaled(target_size, target_size,
                                     Qt.KeepAspectRatioByExpanding,
                                     Qt.SmoothTransformation)
        round_pixmap = self.make_round_pixmap(final_pixmap, target_size)
        self.avatar_label.setPixmap(round_pixmap)
        self.avatar_label.repaint()
        return True

    def select_avatar(self):
        """Открывает диалог выбора файла и загружает выбранное изображение как круглую аватарку."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аватар",
            expanduser("~/Pictures"),
            "Изображения (*.png *.jpg *.jpeg);;Все файлы (*.*)"
        )
        if file_path:
            self.load_avatar_from_file(file_path)

    def load_default_avatar(self):
        """Загружает аватар по умолчанию из resources/account.png (круглый)."""
        default_path = os.path.join("resources", "account.png")
        if os.path.exists(default_path):
            self.load_avatar_from_file(default_path)
        else:
            self.avatar_label.setText("Нет фото")

    # ---------- Стили ----------
    def load_styles(self):
        try:
            with open("resources/main.css", "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("main.css не найден")
            
    def show_join_frame(self):
        self.join_ip_input.clear()
        self.join_port_input.clear()
        self.join_code_input.clear()
        self.join_frame.setVisible(True)

    def hide_join_frame(self):
        self.join_frame.setVisible(False)
        
    def connection(self):
        ip = self.join_ip_input.text().strip()
        port_str = self.join_port_input.text().strip()
        code = self.join_code_input.text().strip()
        name = self.nickname_input.text().strip()
        if not ip or not port_str or not code:
            return
        port = int(port_str)
        self.hide_join_frame()
        p2pManager.client(code, ip, port, name)
        
    def new_session(self):
        p2pManager.start_server()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())