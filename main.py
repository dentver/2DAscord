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

# ── Глобальный хук непойманных исключений ──────────────

from network.logger import _write as _log_write, step_exc as _log_exc

_old_excepthook = sys.excepthook


def _global_excepthook(exctype, value, tb):
    import traceback
    tb_text = "".join(traceback.format_exception(exctype, value, tb))
    _log_write(f"[CRASH] Unhandled exception: {tb_text}")
    if _old_excepthook:
        _old_excepthook(exctype, value, tb)


sys.excepthook = _global_excepthook


def _asyncio_exception_handler(loop, context):
    exc = context.get("exception")
    if exc:
        _log_exc("ASYNCIO", exc)
    else:
        msg = context.get("message", "unknown")
        _log_write(f"[ASYNCIO] {msg}")


# ── Запуск приложения ───────────────────────────────────

if __name__ == "__main__":
    from network.logger import clear as log_clear, step_start, step_ok
    log_clear()
    step_start("APP", "startup")

    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    loop.set_exception_handler(_asyncio_exception_handler)
    asyncio.set_event_loop(loop)
    step_ok("APP", "event loop created")

    from network.ssl_utils import init_rsa_key
    init_rsa_key()
    step_ok("APP", "RSA init started")

    window = MainWindow()
    window.show()
    step_ok("APP", "window shown")

    loop.run_forever()
