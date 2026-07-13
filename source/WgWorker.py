import subprocess

from PyQt6.QtCore import QThread, pyqtSignal

# ─── Worker: запускает wg-quick в отдельном потоке ───────────────────────────


class WgWorker(QThread):
    finished = pyqtSignal(bool, str)  # (success, output)

    def __init__(self, action: str, iface: str):
        super().__init__()
        self.action = action  # "up" | "down"
        self.iface = iface

    def run(self):
        try:
            result = subprocess.run(
                ["sudo", "wg-quick", self.action, self.iface],
                capture_output=True,
                text=True,
                timeout=15,
            )
            ok = result.returncode == 0
            out = result.stdout + result.stderr
            self.finished.emit(ok, out.strip())
        except subprocess.TimeoutExpired:
            self.finished.emit(False, "Timeout: команда выполнялась слишком долго")
        except Exception as e:
            self.finished.emit(False, str(e))
