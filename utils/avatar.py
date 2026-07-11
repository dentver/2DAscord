import sys
import base64
from io import BytesIO
from pathlib import Path

from PIL import Image
from PyQt5.QtCore import Qt, QBuffer
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QImage
from PyQt5.QtWidgets import QLabel, QWidget, QFileDialog


def make_round_pixmap(pixmap: QPixmap, size: int = 75) -> QPixmap:
    if pixmap.isNull():
        return pixmap
    scaled = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    round_pixmap = QPixmap(size, size)
    round_pixmap.fill(Qt.transparent)
    painter = QPainter(round_pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QBrush(scaled))
    painter.setPen(Qt.NoPen)
    painter.drawEllipse(0, 0, size, size)
    painter.end()
    return round_pixmap


def load_avatar_b64(file_path: str) -> str:
    with Image.open(file_path) as img:
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        img.thumbnail((200, 200), Image.Resampling.LANCZOS)
        if img.mode == "RGB":
            img = img.convert("RGBA")
        buf = BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")


def b64_to_pixmap(b64: str) -> QPixmap:
    data = base64.b64decode(b64)
    pixmap = QPixmap()
    pixmap.loadFromData(data, "PNG")
    return pixmap


def make_round_b64(b64: str, size: int = 32) -> str:
    pixmap = b64_to_pixmap(b64)
    round_pixmap = make_round_pixmap(pixmap, size)
    buf = QBuffer()
    buf.open(QBuffer.ReadWrite)
    round_pixmap.save(buf, "PNG")
    b64_result = base64.b64encode(buf.data().data()).decode("utf-8")
    buf.close()
    return b64_result


def set_round_pixmap_on_label(pixmap: QPixmap, avatar_label: QLabel, size: int = 75) -> None:
    round_pixmap = make_round_pixmap(pixmap, size)
    avatar_label.setPixmap(round_pixmap)
    avatar_label.repaint()


def load_from_file_and_display(file_path: str, avatar_label: QLabel) -> str:
    b64 = load_avatar_b64(file_path)
    pixmap = b64_to_pixmap(b64)
    set_round_pixmap_on_label(pixmap, avatar_label)
    return b64


def select_avatar(parent: QWidget, avatar_label: QLabel) -> str:
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Выберите аватар",
        str(Path.home() / "Pictures"),
        "Изображения (*.png *.jpg *.jpeg);;Все файлы (*.*)"
    )
    if file_path:
        return load_from_file_and_display(file_path, avatar_label)
    return ""


def load_default_avatar(avatar_label: QLabel) -> str:
    if getattr(sys, 'frozen', False):
        base = Path(sys._MEIPASS)
    else:
        base = Path.cwd()
    default_path = base / "resources" / "account.png"
    if default_path.exists():
        return load_from_file_and_display(str(default_path), avatar_label)
    avatar_label.setText("Нет фото")
    return ""
