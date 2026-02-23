"""Entry point for Buildozer/Kivy packaging.

This module installs a global excepthook as early as possible so any
import-time or startup exceptions are captured and written to
the app-private Android storage path (`ANDROID_ARGUMENT`) with safe
fallbacks, and prints to stderr/logcat. This helps diagnosing crashes
in built APKs.
"""

import os
import sys
import tempfile
import traceback

# Make stdout/stderr unbuffered in case Android buffers output.
os.environ.setdefault("PYTHONUNBUFFERED", "1")


def _write_crash_log(tb_text: str) -> None:
    # On modern Android, writing directly to /sdcard root often fails due to
    # scoped storage. Prefer app-private storage and safe fallbacks.
    paths = []

    android_argument = os.environ.get("ANDROID_ARGUMENT")
    if android_argument:
        paths.append(os.path.join(android_argument, "gestionfondosm_crash.log"))

    paths.extend(
        [
            "/sdcard/Download/gestionfondosm_crash.log",
            os.path.join(tempfile.gettempdir(), "gestionfondosm_crash.log"),
        ]
    )
    for p in paths:
        try:
            with open(p, "w", encoding="utf-8") as f:
                f.write(tb_text)
            return
        except Exception:
            continue


def _excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    # write to device storage if possible
    try:
        _write_crash_log(tb)
    except Exception:
        pass
    # also print to stderr (shows in logcat)
    try:
        print("[GF_CRASH] Unhandled exception:\n" + tb, file=sys.stderr, flush=True)
    except Exception:
        pass


# Install global excepthook
sys.excepthook = _excepthook


from gf_mobile.main import main


if __name__ == "__main__":
    try:
        main()
    except Exception:
        # main() also may catch exceptions, but keep a last-resort handler
        _excepthook(*sys.exc_info())
