import sys
import os
import PyQt5
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from ui.main_window import MainWindow

qt_plugin_path = str(Path(PyQt5.__file__).parent / "Qt5" / "plugins" / "platforms")
os.environ["QT_QPA_PLATFORM_PLUGIN_PATH"] = qt_plugin_path

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())