"""
WireGuard GUI — прототип
Требования: python >= 3.12, PyQt6
Установка: sudo pacman -S python python-pyqt6
Запуск:     python wireguard-gui.py
"""

from PyQt6.QtGui import QColor, QPalette
from PyQt6.QtWidgets import QApplication

import WgWindow

# ─── Entrypoint ───────────────────────────────────────────────────────────────


def main():
    app = QApplication([])
    app.setApplicationName("WireGuard")
    app.setOrganizationName("devrangers")

    # Тёмная палитра на уровне приложения (для диалогов и пр.)
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor("#1e1e1e"))
    pal.setColor(QPalette.ColorRole.WindowText, QColor("#d4d4d4"))
    app.setPalette(pal)

    win = WgWindow.MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
