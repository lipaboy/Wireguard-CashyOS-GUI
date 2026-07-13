"""
WireGuard GUI — прототип
Требования: python >= 3.12, PyQt6
Установка: sudo pacman -S python python-pyqt6
Запуск:     python wireguard-gui.py
"""

import subprocess
from pathlib import Path

from PyQt6.QtGui import QColor, QFont, QIcon, QPalette
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import WgWorker

WG_CONFIG_DIR = Path("/etc/wireguard")

ICON_PATHS = [
    Path(__file__).parent / "../wg.png",
    # Path.home() / ".local/share/icons/wireguard.png",
    # Path("/usr/share/icons/wireguard.png"),
]


def _make_icon() -> QIcon:
    for p in ICON_PATHS:
        if p.exists():
            return QIcon(str(p))
    return QIcon.fromTheme("network-vpn")


# ─── Главное окно ─────────────────────────────────────────────────────────────


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WireGuard")
        self.setMinimumSize(800, 520)
        self._icon = _make_icon()
        self.setWindowIcon(self._icon)
        self._worker = None
        self._active_iface = None  # имя активного интерфейса

        self._build_ui()
        self._apply_style()
        self._load_configs()
        self._detect_active()

    # ── Построение UI ──────────────────────────────────────────────────────────

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)

        # ── Левая панель: список туннелей ──────────────────────────────────────
        left = QWidget()
        left.setObjectName("leftPanel")
        left.setFixedWidth(220)
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        list_label = QLabel("  Туннели")
        list_label.setObjectName("listHeader")
        list_label.setFixedHeight(36)
        lv.addWidget(list_label)

        self.tunnel_list = QListWidget()
        self.tunnel_list.setObjectName("tunnelList")
        self.tunnel_list.currentItemChanged.connect(self._on_select)
        lv.addWidget(self.tunnel_list)

        # ── Правая панель: детали + кнопки ────────────────────────────────────
        right = QWidget()
        right.setObjectName("rightPanel")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(20, 16, 20, 16)
        rv.setSpacing(12)

        # Заголовок + статус
        title_row = QHBoxLayout()
        self.title_label = QLabel("Выберите туннель")
        self.title_label.setObjectName("titleLabel")
        title_row.addWidget(self.title_label)
        title_row.addStretch()

        self.status_badge = QLabel()
        self.status_badge.setObjectName("statusBadge")
        self.status_badge.setFixedHeight(24)
        title_row.addWidget(self.status_badge)
        rv.addLayout(title_row)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setObjectName("separator")
        rv.addWidget(sep)

        # Содержимое конфига
        config_lbl = QLabel("Конфигурация:")
        config_lbl.setObjectName("sectionLabel")
        rv.addWidget(config_lbl)

        self.config_view = QTextEdit()
        self.config_view.setObjectName("configView")
        self.config_view.setReadOnly(True)
        self.config_view.setFont(QFont("Monospace", 10))
        rv.addWidget(self.config_view)

        # Лог вывода команд
        log_lbl = QLabel("Вывод:")
        log_lbl.setObjectName("sectionLabel")
        rv.addWidget(log_lbl)

        self.log_view = QTextEdit()
        self.log_view.setObjectName("logView")
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Monospace", 9))
        self.log_view.setFixedHeight(90)
        rv.addWidget(self.log_view)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_up = QPushButton("▶  Подключить")
        self.btn_up.setObjectName("btnUp")
        self.btn_up.setFixedSize(150, 36)
        self.btn_up.clicked.connect(self._on_up)
        self.btn_up.setEnabled(False)
        btn_row.addWidget(self.btn_up)

        self.btn_down = QPushButton("■  Отключить")
        self.btn_down.setObjectName("btnDown")
        self.btn_down.setFixedSize(150, 36)
        self.btn_down.clicked.connect(self._on_down)
        self.btn_down.setEnabled(False)
        btn_row.addWidget(self.btn_down)

        rv.addLayout(btn_row)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        root.addWidget(splitter)

    # ── Загрузка конфигов ──────────────────────────────────────────────────────

    def _load_configs(self):
        self.tunnel_list.clear()
        if not WG_CONFIG_DIR.exists():
            self._log(f"Директория {WG_CONFIG_DIR} не найдена")
            return

        configs = sorted(WG_CONFIG_DIR.glob("*.conf"))
        if not configs:
            self._log("Конфиги не найдены в /etc/wireguard")
            return

        for cfg in configs:
            iface = cfg.stem
            item = QListWidgetItem(f"  {iface}")
            item.setData(Qt.ItemDataRole.UserRole, iface)
            self.tunnel_list.addItem(item)

    def _detect_active(self):
        """Определяем уже запущенные wg интерфейсы через `wg show`."""
        try:
            r = subprocess.run(
                ["wg", "show", "interfaces"], capture_output=True, text=True
            )
            active = r.stdout.strip().split()
            self._active_iface = active[0] if active else None
        except Exception:
            self._active_iface = None
        self._refresh_list_icons()

    def _refresh_list_icons(self):
        for i in range(self.tunnel_list.count()):
            item = self.tunnel_list.item(i)
            if not item:
                return
            iface = item.data(Qt.ItemDataRole.UserRole)
            if iface == self._active_iface:
                item.setText(f"  🟢 {iface}")
            else:
                item.setText(f"  ⬜ {iface}")

    # ── Выбор туннеля ──────────────────────────────────────────────────────────

    def _on_select(self, current, _prev):
        if current is None:
            return
        iface = current.data(Qt.ItemDataRole.UserRole)
        cfg_path = WG_CONFIG_DIR / f"{iface}.conf"

        self.title_label.setText(iface)

        # Читаем конфиг (приватные ключи маскируем)
        try:
            text = cfg_path.read_text()
            text = self._mask_keys(text)
            self.config_view.setPlainText(text)
        except PermissionError:
            self.config_view.setPlainText("⚠ Нет прав на чтение. Запустите с sudo.")
        except Exception as e:
            self.config_view.setPlainText(str(e))

        is_active = iface == self._active_iface
        self._set_status(is_active)
        self.btn_up.setEnabled(not is_active)
        self.btn_down.setEnabled(is_active)

    def _mask_keys(self, text: str) -> str:
        """Маскируем PrivateKey в отображении."""
        lines = []
        for line in text.splitlines():
            if line.strip().lower().startswith("privatekey"):
                k, _, _ = line.partition("=")
                lines.append(f"{k.rstrip()} = <скрыто>")
            else:
                lines.append(line)
        return "\n".join(lines)

    def _set_status(self, active: bool):
        if active:
            self.status_badge.setText(" ● Активен ")
            self.status_badge.setStyleSheet(
                "background:#2d6a2d; color:#7fff7f; border-radius:4px; padding:0 6px;"
            )
        else:
            self.status_badge.setText(" ○ Не активен ")
            self.status_badge.setStyleSheet(
                "background:#444; color:#aaa; border-radius:4px; padding:0 6px;"
            )

    # ── Команды wg-quick ───────────────────────────────────────────────────────

    def _current_iface(self):
        item = self.tunnel_list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item else None

    def _on_up(self):
        iface = self._current_iface()
        if iface:
            self._run_wg("up", iface)

    def _on_down(self):
        iface = self._current_iface()
        if iface:
            self._run_wg("down", iface)

    def _run_wg(self, action: str, iface: str):
        self.btn_up.setEnabled(False)
        self.btn_down.setEnabled(False)
        self._log(f"$ sudo wg-quick {action} {iface}")

        self._worker = WgWorker.WgWorker(action, iface)
        self._worker.finished.connect(self._on_wg_done)
        self._worker.start()

    def _on_wg_done(self, ok: bool, output: str):
        self._log(output if output else ("OK" if ok else "Ошибка"))
        if ok:
            iface = self._current_iface()
            # Обновляем активный интерфейс
            self._detect_active()
            is_active = iface == self._active_iface
            self._set_status(is_active)
            self.btn_up.setEnabled(not is_active)
            self.btn_down.setEnabled(is_active)
        else:
            # Возвращаем кнопки в прежнее состояние
            iface = self._current_iface()
            is_active = iface == self._active_iface
            self.btn_up.setEnabled(not is_active)
            self.btn_down.setEnabled(is_active)

    def _log(self, msg: str):
        self.log_view.append(msg)
        sb = self.log_view.verticalScrollBar()
        if not sb:
            return
        sb.setValue(sb.maximum())

    # ── Стили ──────────────────────────────────────────────────────────────────

    def _apply_style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background: #1e1e1e;
                color: #d4d4d4;
            }
            #leftPanel {
                background: #252526;
                border-right: 1px solid #333;
            }
            #listHeader {
                background: #2d2d2d;
                color: #aaa;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
                border-bottom: 1px solid #333;
            }
            #tunnelList {
                background: #252526;
                border: none;
                font-size: 13px;
                outline: none;
            }
            #tunnelList::item {
                padding: 8px 4px;
                border-bottom: 1px solid #2e2e2e;
            }
            #tunnelList::item:selected {
                background: #094771;
                color: #fff;
            }
            #tunnelList::item:hover:!selected {
                background: #2a2d2e;
            }
            #rightPanel {
                background: #1e1e1e;
            }
            #titleLabel {
                font-size: 16px;
                font-weight: bold;
                color: #e0e0e0;
            }
            #separator {
                color: #333;
            }
            #sectionLabel {
                color: #888;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            #configView, #logView {
                background: #141414;
                border: 1px solid #333;
                border-radius: 4px;
                color: #c8c8c8;
                selection-background-color: #094771;
            }
            #logView {
                color: #9cdcfe;
            }
            #btnUp {
                background: #0e6a0e;
                color: #fff;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            #btnUp:hover  { background: #1a8a1a; }
            #btnUp:disabled { background: #333; color: #666; }

            #btnDown {
                background: #8b1a1a;
                color: #fff;
                border: none;
                border-radius: 4px;
                font-size: 13px;
            }
            #btnDown:hover  { background: #b02020; }
            #btnDown:disabled { background: #333; color: #666; }

            QSplitter::handle {
                background: #333;
            }
            QScrollBar:vertical {
                background: #1e1e1e;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 4px;
                min-height: 20px;
            }
        """)


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

    win = MainWindow()
    win.show()
    app.exec()


if __name__ == "__main__":
    main()
