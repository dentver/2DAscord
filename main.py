import sys
import os
import asyncio
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from qasync import QEventLoop

from ui.main_window import MainWindow

if getattr(sys, 'frozen', False):
    base = Path(sys._MEIPASS)
else:
    import PyQt5
    base = Path(PyQt5.__file__).parent

qt_plugin_path = str(base / "Qt5" / "plugins" / "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    window.show()

    loop.run_forever()
