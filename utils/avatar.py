from pathlib import Path
from PIL import Image
from PyQt5.QtCore import Qt
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


def load_avatar_from_file(file_path: str, avatar_label: QLabel, target_size: int = 75) -> bool:
    with Image.open(file_path) as pil_image:
        if pil_image.mode not in ("RGB", "RGBA"):
            pil_image = pil_image.convert("RGB")
        pil_image.thumbnail((400, 400), Image.Resampling.LANCZOS)
        if pil_image.mode == "RGB":
            pil_image = pil_image.convert("RGBA")
        data = pil_image.tobytes("raw", "RGBA")
        qimage = QImage(data, pil_image.width, pil_image.height, QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(qimage)

    final_pixmap = pixmap.scaled(
        target_size, target_size,
        Qt.KeepAspectRatioByExpanding,
        Qt.SmoothTransformation
    )
    round_pixmap = make_round_pixmap(final_pixmap, target_size)
    avatar_label.setPixmap(round_pixmap)
    avatar_label.repaint()
    return True


def select_avatar(parent: QWidget, avatar_label: QLabel) -> None:
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Выберите аватар",
        str(Path.home() / "Pictures"),
        "Изображения (*.png *.jpg *.jpeg);;Все файлы (*.*)"
    )
    if file_path:
        load_avatar_from_file(file_path, avatar_label)


def load_default_avatar(avatar_label: QLabel) -> None:
    default_path = Path("resources") / "account.png"
    if default_path.exists():
        load_avatar_from_file(str(default_path), avatar_label)
    else:
        avatar_label.setText("Нет фото")
