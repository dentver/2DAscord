import sys
import os
import asyncio
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from qasync import QEventLoop

from ui.main_window import MainWindow

# ── Путь к плагинам Qt (для сборки) ─────────────────────

if getattr(sys, 'frozen', False):
    pyqt_path = Path(sys._MEIPASS) / "PyQt5" / "Qt5"
    if not pyqt_path.is_dir():
        pyqt_path = Path(sys._MEIPASS) / "PyQt5" / "Qt"
    qt_plugin_path = str(pyqt_path / "plugins" / "platforms")
    if Path(qt_plugin_path).is_dir():
        os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path
else:
    import PyQt5
    base = Path(PyQt5.__file__).parent
    qt_plugin_path = str(base / "Qt5" / "plugins" / "platforms")
    os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path

# ── Запуск приложения ───────────────────────────────────

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    loop.run_forever()
