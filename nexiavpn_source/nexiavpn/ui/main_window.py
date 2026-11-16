"""
NexiaVPN - Main Window
"""
import os
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QFrame, QSizePolicy, QMessageBox, QInputDialog,
    QScrollArea, QApplication, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QObject, QTimer, QSize
from PySide6.QtGui import QFont, QColor, QIcon, QPixmap, QPainter, QLinearGradient

from ui.widgets import ConnectButton, ServerCard, StatusBar, GlassPanel
from ui.stylesheet import MAIN_STYLE, SERVER_LIST_STYLE
from ui.add_server_dialog import AddServerDialog
from ui.settings_dialog import SettingsDialog
from core.engine import XrayEngine, ConnectionState
from core.server_storage import ServerStorage, SettingsStorage
from core.link_parser import LinkParser
from utils.logger import get_logger
from utils.geo import lookup_ip_country

logger = get_logger()


class MainWindow(QMainWindow):
    _ping_signal = Signal(object)   # for thread-safe ping update
    _state_signal = Signal(object, str)  # for thread-safe state update

    def __init__(self):
        super().__init__()
        self.setWindowTitle("NexiaVPN")
        self.setMinimumSize(900, 640)
        self.resize(1000, 700)
        
        self._storage = ServerStorage()
        self._settings = SettingsStorage()
        self._engine = XrayEngine()
        self._active_server_id = None
        self._server_widgets = {}   # id -> ServerCard
        
        # Wire engine callbacks to Qt signals
        self._ping_signal.connect(self._on_ping_update)
        self._state_signal.connect(self._on_state_change)
        
        self._engine.on_state_change = lambda s, e: self._state_signal.emit(s, e)
        self._engine.on_ping_update = lambda p: self._ping_signal.emit(p)
        
        self.setStyleSheet(MAIN_STYLE)
        self._setup_ui()
        self._load_servers()
        self._setup_tray()
        
        # Auto-connect
        if self._settings.get("auto_connect", False):
            last_id = self._settings.get("last_server_id")
            if last_id:
                QTimer.singleShot(500, lambda: self._connect_server(last_id))

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("centralWidget")
        self.setCentralWidget(central)
        
        root_layout = QVBoxLayout(central)
        root_layout.setSpacing(0)
        root_layout.setContentsMargins(0, 0, 0, 0)
        
        # === Top bar ===
        topbar = self._build_topbar()
        root_layout.addWidget(topbar)
        
        # === Main content ===
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Left panel - connect button
        left_panel = self._build_left_panel()
        content_layout.addWidget(left_panel, stretch=0)
        
        # Separator
        sep = QFrame()
        sep.setFixedWidth(1)
        sep.setStyleSheet("background: #1a2440;")
        content_layout.addWidget(sep)
        
        # Right panel - server list
        right_panel = self._build_right_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        root_layout.addWidget(content, stretch=1)
        
        # === Status bar ===
        self._status_bar = StatusBar()
        root_layout.addWidget(self._status_bar)

    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet("background: #080c18; border-bottom: 1px solid #1a2440;")
        
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        
        # Logo
        logo_lbl = QLabel()
        logo_lbl.setText(
            '<span style="color:#818cf8; font-size:18px; font-weight:900; letter-spacing:2px">NEXIA</span>'
            '<span style="color:#6366f1; font-size:18px; font-weight:400">VPN</span>'
        )
        layout.addWidget(logo_lbl)
        layout.addStretch()
        
        # Nav buttons
        for text, slot in [("Серверы", None), ("Статистика", None)]:
            btn = QPushButton(text)
            btn.setStyleSheet("""
                QPushButton { background: transparent; color: #64748b; border: none;
                             padding: 6px 14px; font-size: 13px; border-radius: 6px; }
                QPushButton:hover { color: #94a3b8; background: rgba(255,255,255,0.05); }
            """)
            layout.addWidget(btn)
        
        layout.addSpacing(8)
        
        # Settings button
        settings_btn = QPushButton("⚙")
        settings_btn.setToolTip("Настройки")
        settings_btn.setStyleSheet("""
            QPushButton { background: transparent; color: #64748b; border: none;
                         padding: 6px 12px; font-size: 16px; border-radius: 6px; }
            QPushButton:hover { color: #818cf8; background: rgba(99,102,241,0.1); }
        """)
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)
        
        return bar

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        panel.setFixedWidth(320)
        panel.setStyleSheet("background: #080c18;")
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(24, 32, 24, 24)
        layout.setSpacing(20)
        
        # Connect button
        btn_container = QWidget()
        btn_cl = QHBoxLayout(btn_container)
        btn_cl.setContentsMargins(0, 0, 0, 0)
        self._connect_btn = ConnectButton()
        self._connect_btn.clicked.connect(self._toggle_connection)
        btn_cl.addWidget(self._connect_btn, alignment=Qt.AlignCenter)
        layout.addWidget(btn_container)
        
        # Connection info card
        info_frame = GlassPanel()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setContentsMargins(16, 14, 16, 14)
        info_layout.setSpacing(8)
        
        self._server_name_lbl = QLabel("Сервер не выбран")
        self._server_name_lbl.setFont(QFont("Segoe UI", 13, QFont.Medium))
        self._server_name_lbl.setStyleSheet("color: #94a3b8;")
        self._server_name_lbl.setWordWrap(True)
        
        self._server_detail_lbl = QLabel("")
        self._server_detail_lbl.setFont(QFont("Segoe UI", 11))
        self._server_detail_lbl.setStyleSheet("color: #4a5568;")
        
        info_layout.addWidget(self._server_name_lbl)
        info_layout.addWidget(self._server_detail_lbl)
        layout.addWidget(info_frame)
        
        # Traffic info (placeholder)
        traffic_frame = GlassPanel()
        tf_layout = QHBoxLayout(traffic_frame)
        tf_layout.setContentsMargins(16, 12, 16, 12)
        
        for icon, label_attr, default in [
            ("↑", "_upload_lbl", "0 B/s"),
            ("↓", "_download_lbl", "0 B/s"),
        ]:
            col = QVBoxLayout()
            col.setSpacing(2)
            icon_lbl = QLabel(icon)
            icon_lbl.setStyleSheet(f"color: {'#818cf8' if icon == '↑' else '#34d399'}; font-size: 16px; font-weight: bold;")
            icon_lbl.setAlignment(Qt.AlignCenter)
            val_lbl = QLabel(default)
            val_lbl.setStyleSheet("color: #64748b; font-size: 11px;")
            val_lbl.setAlignment(Qt.AlignCenter)
            setattr(self, label_attr, val_lbl)
            col.addWidget(icon_lbl)
            col.addWidget(val_lbl)
            tf_layout.addLayout(col)
            if icon == "↑":
                sep2 = QFrame()
                sep2.setFrameShape(QFrame.VLine)
                sep2.setStyleSheet("color: #1e2535;")
                tf_layout.addWidget(sep2)
        
        layout.addWidget(traffic_frame)
        layout.addStretch()
        
        # Proxy info
        proxy_port = self._settings.get("proxy_port", 10808)
        self._proxy_info = QLabel(f"HTTP Прокси: 127.0.0.1:{proxy_port}")
        self._proxy_info.setStyleSheet("color: #374151; font-size: 11px;")
        self._proxy_info.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._proxy_info)
        
        return panel

    def _build_right_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #0a0e1a; border-bottom: 1px solid #1a2440;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 20, 0)
        
        servers_title = QLabel("Серверы")
        servers_title.setFont(QFont("Segoe UI", 14, QFont.Medium))
        servers_title.setStyleSheet("color: #e2e8f0;")
        h_layout.addWidget(servers_title)
        h_layout.addStretch()
        
        self._server_count_lbl = QLabel("0 серверов")
        self._server_count_lbl.setStyleSheet("color: #4a5568; font-size: 12px;")
        h_layout.addWidget(self._server_count_lbl)
        
        h_layout.addSpacing(12)
        
        add_btn = QPushButton("+ Добавить")
        add_btn.setStyleSheet("""
            QPushButton { background: rgba(99,102,241,0.15); color: #818cf8; border: 1px solid rgba(99,102,241,0.3);
                         padding: 7px 16px; border-radius: 8px; font-size: 12px; font-weight: 600; }
            QPushButton:hover { background: rgba(99,102,241,0.25); border-color: rgba(99,102,241,0.5); }
        """)
        add_btn.clicked.connect(self._open_add_server)
        h_layout.addWidget(add_btn)
        
        layout.addWidget(header)
        
        # Server list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #0a0e1a; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: #0a0e1a;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setContentsMargins(12, 12, 12, 12)
        self._list_layout.setSpacing(6)
        self._list_layout.addStretch()
        
        scroll.setWidget(self._list_container)
        layout.addWidget(scroll, stretch=1)
        
        # Empty state
        self._empty_label = QLabel(
            "⚡  Нет серверов\n\nНажмите «+ Добавить» и вставьте VPN-ссылку\n"
            "vless:// · vmess:// · trojan:// · ss://"
        )
        self._empty_label.setAlignment(Qt.AlignCenter)
        self._empty_label.setStyleSheet("color: #374151; font-size: 14px; line-height: 1.8;")
        self._empty_label.setVisible(True)
        layout.addWidget(self._empty_label, alignment=Qt.AlignCenter)
        
        return panel

    def _setup_tray(self):
        self._tray = QSystemTrayIcon(self)
        icon = self._get_app_icon()
        if icon:
            self._tray.setIcon(icon)
        
        tray_menu = QMenu()
        tray_menu.setStyleSheet("""
            QMenu { background: #131929; border: 1px solid #2d3f5e; }
            QMenu::item { padding: 8px 20px; color: #e2e8f0; }
            QMenu::item:selected { background: #2d3f5e; }
        """)
        
        show_action = tray_menu.addAction("Открыть NexiaVPN")
        show_action.triggered.connect(self.show)
        
        tray_menu.addSeparator()
        
        self._tray_connect = tray_menu.addAction("Подключить")
        self._tray_connect.triggered.connect(self._toggle_connection)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Выйти")
        quit_action.triggered.connect(QApplication.quit)
        
        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.show()

    def _get_app_icon(self) -> QIcon:
        icon_path = os.path.join("assets", "icon.png")
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        # Generate simple icon
        pix = QPixmap(32, 32)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 32, 32)
        grad.setColorAt(0, QColor("#4f46e5"))
        grad.setColorAt(1, QColor("#7c3aed"))
        from PySide6.QtGui import QBrush
        p.setBrush(QBrush(grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(2, 2, 28, 28)
        p.setPen(QColor("white"))
        p.setFont(QFont("Segoe UI", 14, QFont.Bold))
        p.drawText(pix.rect(), Qt.AlignCenter, "N")
        p.end()
        return QIcon(pix)

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()

    # ===== Server management =====
    
    def _load_servers(self):
        servers = self._storage.get_all()
        for server in servers:
            self._add_server_card(server)
        self._update_empty_state()

    def _add_server_card(self, server: dict):
        card = ServerCard(
            server_id=server["id"],
            name=server.get("name", "Unknown"),
            protocol=server.get("protocol", "?"),
            address=server.get("address", ""),
            country=server.get("country", ""),
            is_active=(server["id"] == self._active_server_id)
        )
        card.connect_requested.connect(self._connect_server)
        card.rename_requested.connect(self._rename_server)
        card.delete_requested.connect(self._delete_server)
        
        # Insert before stretch
        idx = self._list_layout.count() - 1
        self._list_layout.insertWidget(idx, card)
        self._server_widgets[server["id"]] = card
        
        # Async ping measurement
        cfg = self._storage.get_server_config(server["id"])
        if cfg:
            self._engine.measure_server_ping(cfg, lambda p, sid=server["id"]: self._on_server_ping(sid, p))

    def _on_server_ping(self, server_id: str, ping):
        if server_id in self._server_widgets:
            card = self._server_widgets[server_id]
            card.set_ping(ping)

    def _update_empty_state(self):
        has_servers = len(self._server_widgets) > 0
        self._empty_label.setVisible(not has_servers)
        count = len(self._server_widgets)
        noun = "сервер" if count == 1 else ("сервера" if 2 <= count <= 4 else "серверов")
        self._server_count_lbl.setText(f"{count} {noun}" if count else "")

    def _open_add_server(self):
        dialog = AddServerDialog(self)
        dialog.server_added.connect(self._on_server_added)
        dialog.exec()

    def _on_server_added(self, cfg):
        # Look up country asynchronously
        def on_country(country_code):
            if country_code:
                cfg.country = country_code
            server_id = self._storage.add_server(cfg)
            if country_code:
                self._storage.update_country(server_id, country_code)
            
            # Add to UI - must run on main thread
            servers = self._storage.get_all()
            new_server = next((s for s in servers if s["id"] == server_id), None)
            if new_server:
                self._add_server_card(new_server)
                self._update_empty_state()
            logger.info(f"Server added: {cfg.name}")
        
        # Try GeoIP for server address
        if cfg.address and not cfg.address.replace(".", "").isdigit():
            # Hostname, resolve first
            import socket
            try:
                ip = socket.gethostbyname(cfg.address)
                lookup_ip_country(ip, on_country)
            except Exception:
                on_country(None)
        elif cfg.address:
            lookup_ip_country(cfg.address, on_country)
        else:
            on_country(None)

    def _rename_server(self, server_id: str):
        server = next((s for s in self._storage.get_all() if s["id"] == server_id), None)
        if not server:
            return
        
        name, ok = QInputDialog.getText(
            self, "Переименовать сервер",
            "Новое имя:", text=server["name"]
        )
        if ok and name.strip():
            self._storage.rename_server(server_id, name.strip())
            if server_id in self._server_widgets:
                card = self._server_widgets[server_id]
                card.name_label.setText(name.strip())

    def _delete_server(self, server_id: str):
        reply = QMessageBox.question(
            self, "Удалить сервер",
            "Вы уверены, что хотите удалить этот сервер?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if server_id == self._active_server_id:
                self._engine.disconnect()
            
            if server_id in self._server_widgets:
                card = self._server_widgets.pop(server_id)
                self._list_layout.removeWidget(card)
                card.deleteLater()
            
            self._storage.remove_server(server_id)
            self._update_empty_state()

    # ===== Connection =====
    
    def _toggle_connection(self):
        if self._engine.state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            self._engine.disconnect()
            self._active_server_id = None
        else:
            # Connect to first available or last used
            last_id = self._settings.get("last_server_id")
            servers = self._storage.get_all()
            
            if not servers:
                QMessageBox.information(self, "Нет серверов",
                    "Добавьте хотя бы один сервер, нажав «+ Добавить».")
                return
            
            if last_id and any(s["id"] == last_id for s in servers):
                self._connect_server(last_id)
            else:
                self._connect_server(servers[0]["id"])

    def _connect_server(self, server_id: str):
        cfg = self._storage.get_server_config(server_id)
        if not cfg:
            QMessageBox.warning(self, "Ошибка", "Не удалось прочитать конфигурацию сервера.")
            return
        
        # Update UI
        for sid, card in self._server_widgets.items():
            card.set_active(sid == server_id)
        
        self._active_server_id = server_id
        self._settings.set("last_server_id", server_id)
        
        server = next((s for s in self._storage.get_all() if s["id"] == server_id), {})
        self._server_name_lbl.setText(server.get("name", cfg.name))
        self._server_detail_lbl.setText(f"{cfg.protocol.upper()} · {cfg.address}:{cfg.port}")
        
        self._engine.connect(cfg)

    # ===== Engine callbacks (Qt signals) =====
    
    def _on_state_change(self, state: ConnectionState, error: str):
        if state == ConnectionState.CONNECTING:
            self._connect_btn.set_state("connecting")
            self._status_bar.set_connecting()
            self._tray_connect.setText("Отключить")
        
        elif state == ConnectionState.CONNECTED:
            self._connect_btn.set_state("connected")
            proxy_port = self._settings.get("proxy_port", 10808)
            server_name = self._server_name_lbl.text()
            self._status_bar.set_connected(server_name, proxy_port)
            self._tray.showMessage("NexiaVPN", f"Подключено: {server_name}", 
                                   QSystemTrayIcon.Information, 2000)
            self._proxy_info.setText(f"HTTP Прокси: 127.0.0.1:{proxy_port}")
        
        elif state == ConnectionState.DISCONNECTED:
            self._connect_btn.set_state("idle")
            self._status_bar.set_disconnected()
            self._tray_connect.setText("Подключить")
            for card in self._server_widgets.values():
                card.set_active(False)
            self._active_server_id = None
        
        elif state == ConnectionState.ERROR:
            self._connect_btn.set_state("error")
            self._status_bar.set_error(error[:60] if error else "Неизвестная ошибка")
            self._tray_connect.setText("Подключить")
            self._active_server_id = None
            for card in self._server_widgets.values():
                card.set_active(False)
            if error:
                QMessageBox.warning(self, "Ошибка подключения", error)
        
        elif state == ConnectionState.DISCONNECTING:
            self._connect_btn.set_state("idle")

    def _on_ping_update(self, ping):
        self._status_bar.set_ping(ping)
        if self._active_server_id and self._active_server_id in self._server_widgets:
            self._server_widgets[self._active_server_id].set_ping(ping)

    # ===== Settings =====
    
    def _open_settings(self):
        dialog = SettingsDialog(self._settings, self)
        dialog.settings_changed.connect(self._on_settings_changed)
        dialog.exec()

    def _on_settings_changed(self):
        proxy_port = self._settings.get("proxy_port", 10808)
        self._proxy_info.setText(f"HTTP Прокси: 127.0.0.1:{proxy_port}")
        self._engine._settings = self._settings

    # ===== Window events =====
    
    def closeEvent(self, event):
        # Minimize to tray instead of closing
        event.ignore()
        self.hide()
        self._tray.showMessage("NexiaVPN", "Работает в фоне. Дважды нажмите иконку для открытия.",
                               QSystemTrayIcon.Information, 2000)
