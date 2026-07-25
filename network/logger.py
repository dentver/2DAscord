import sys
import traceback
from pathlib import Path


# ── Logger ──────────────────────────────────────────


_LOG_FILE = Path.cwd() / "log.txt"


def _write(msg: str):
    try:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
            f.flush()
    except Exception:
        pass


def log(step: str, status: str, detail: str = ""):
    line = f"[{step}] {status}"
    if detail:
        line += f" | {detail}"
    _write(line)
    print(line, file=sys.stderr)


def clear():
    try:
        _LOG_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass


def step_start(step: str, detail: str = ""):
    log(step, "START", detail)


def step_ok(step: str, detail: str = ""):
    log(step, "OK", detail)


def step_fail(step: str, detail: str = ""):
    log(step, "FAIL", detail)


def step_exc(step: str, exc: BaseException):
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    for line in tb.strip().split("\n"):
        _write(f"[{step}] TRACE | {line}")
    print(tb, file=sys.stderr, end="")