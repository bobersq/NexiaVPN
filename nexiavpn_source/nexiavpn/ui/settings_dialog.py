"""
Settings Dialog
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QSpinBox, QFrame,
    QTabWidget, QWidget, QFormLayout, QGroupBox
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont

from core.server_storage import SettingsStorage


class SettingsDialog(QDialog):
    settings_changed = Signal()
    
    def __init__(self, settings: SettingsStorage, parent=None):
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("Настройки NexiaVPN")
        self.setMinimumSize(500, 480)
        self.setModal(True)
        
        self._setup_ui()
        self._load_values()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: #0a0e1a; }
            QTabWidget::pane {
                background: #0d1424;
                border: 1px solid #1e2535;
                border-radius: 8px;
            }
            QTabBar::tab {
                background: #0d1424;
                color: #64748b;
                padding: 10px 20px;
                border: none;
                border-bottom: 2px solid transparent;
                font-size: 13px;
            }
            QTabBar::tab:selected {
                color: #818cf8;
                border-bottom-color: #6366f1;
            }
            QTabBar::tab:hover { color: #94a3b8; }
            QGroupBox {
                color: #64748b;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
                border: none;
                border-top: 1px solid #1e2535;
                margin-top: 12px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                top: -1px;
                background: #0d1424;
                padding: 0 6px;
            }
            QLabel { color: #94a3b8; }
            QLineEdit, QSpinBox, QComboBox {
                background: #131929;
                border: 1px solid #2d3f5e;
                border-radius: 6px;
                padding: 8px 12px;
                color: #e2e8f0;
                min-width: 180px;
            }
            QLineEdit:focus, QSpinBox:focus { border-color: #6366f1; }
            QCheckBox { color: #94a3b8; spacing: 8px; }
            QCheckBox::indicator {
                width: 18px; height: 18px;
                border: 2px solid #2d3f5e;
                border-radius: 4px;
                background: #0a0e1a;
            }
            QCheckBox::indicator:checked {
                background: #6366f1;
                border-color: #6366f1;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("⚙️  Настройки")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #e2e8f0; margin-bottom: 4px;")
        layout.addWidget(title)
        
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # === General Tab ===
        general = QWidget()
        g_layout = QVBoxLayout(general)
        g_layout.setContentsMargins(16, 16, 16, 16)
        g_layout.setSpacing(12)
        
        startup_group = QGroupBox("ЗАПУСК")
        sg_layout = QVBoxLayout(startup_group)
        sg_layout.setSpacing(10)
        self.auto_connect = QCheckBox("Автоподключение при запуске")
        self.run_startup = QCheckBox("Запускать вместе с Windows")
        sg_layout.addWidget(self.auto_connect)
        sg_layout.addWidget(self.run_startup)
        g_layout.addWidget(startup_group)
        
        lang_group = QGroupBox("ИНТЕРФЕЙС")
        lg_layout = QFormLayout(lang_group)
        self.language = QComboBox()
        self.language.addItems(["Русский", "English"])
        lg_layout.addRow("Язык:", self.language)
        g_layout.addWidget(lang_group)
        
        g_layout.addStretch()
        tabs.addTab(general, "Основные")
        
        # === Network Tab ===
        network = QWidget()
        n_layout = QVBoxLayout(network)
        n_layout.setContentsMargins(16, 16, 16, 16)
        n_layout.setSpacing(12)
        
        proxy_group = QGroupBox("ПРОКСИ")
        pg_layout = QFormLayout(proxy_group)
        self.http_port = QSpinBox()
        self.http_port.setRange(1024, 65535)
        self.socks_port = QSpinBox()
        self.socks_port.setRange(1024, 65535)
        self.allow_lan = QCheckBox("Разрешить подключения из LAN")
        pg_layout.addRow("HTTP порт:", self.http_port)
        pg_layout.addRow("SOCKS5 порт:", self.socks_port)
        pg_layout.addRow("", self.allow_lan)
        n_layout.addWidget(proxy_group)
        
        routing_group = QGroupBox("МАРШРУТИЗАЦИЯ")
        rg_layout = QFormLayout(routing_group)
        self.routing_mode = QComboBox()
        self.routing_mode.addItem("Только прокси", "proxy")
        self.routing_mode.addItem("Глобальный (всё через VPN)", "global")
        self.routing_mode.addItem("Обход CN (Китай напрямую)", "bypass_cn")
        rg_layout.addRow("Режим:", self.routing_mode)
        n_layout.addWidget(routing_group)
        
        dns_group = QGroupBox("DNS")
        dg_layout = QFormLayout(dns_group)
        self.dns_primary = QLineEdit()
        self.dns_primary.setPlaceholderText("1.1.1.1")
        self.dns_secondary = QLineEdit()
        self.dns_secondary.setPlaceholderText("8.8.8.8")
        dg_layout.addRow("Основной DNS:", self.dns_primary)
        dg_layout.addRow("Резервный DNS:", self.dns_secondary)
        n_layout.addWidget(dns_group)
        
        n_layout.addStretch()
        tabs.addTab(network, "Сеть")
        
        # === About Tab ===
        about = QWidget()
        ab_layout = QVBoxLayout(about)
        ab_layout.setContentsMargins(16, 16, 16, 16)
        ab_layout.setAlignment(Qt.AlignCenter)
        
        ab_title = QLabel("NexiaVPN")
        ab_title.setFont(QFont("Segoe UI", 20, QFont.Bold))
        ab_title.setStyleSheet("color: #818cf8;")
        ab_title.setAlignment(Qt.AlignCenter)
        
        ab_ver = QLabel("Версия 1.0.0")
        ab_ver.setStyleSheet("color: #64748b;")
        ab_ver.setAlignment(Qt.AlignCenter)
        
        ab_desc = QLabel("Поддерживаемые протоколы:\nVLESS · VMess · Trojan · Shadowsocks\n\nДвижок: Xray-core\nUI: Python + PySide6")
        ab_desc.setAlignment(Qt.AlignCenter)
        ab_desc.setStyleSheet("color: #94a3b8; line-height: 1.8;")
        
        ab_layout.addStretch()
        ab_layout.addWidget(ab_title)
        ab_layout.addSpacing(8)
        ab_layout.addWidget(ab_ver)
        ab_layout.addSpacing(16)
        ab_layout.addWidget(ab_desc)
        ab_layout.addStretch()
        tabs.addTab(about, "О программе")
        
        # === Buttons ===
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton { background: #1e2535; color: #94a3b8; border: 1px solid #2d3f5e;
                         padding: 10px 24px; border-radius: 8px; }
            QPushButton:hover { background: #2d3f5e; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        save_btn = QPushButton("Сохранить")
        save_btn.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                             stop:0 #4f46e5, stop:1 #7c3aed);
                         color: white; border: none; padding: 10px 24px;
                         border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                             stop:0 #4338ca, stop:1 #6d28d9); }
        """)
        save_btn.clicked.connect(self._save)
        
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def _load_values(self):
        s = self._settings
        self.auto_connect.setChecked(s.get("auto_connect", False))
        self.run_startup.setChecked(s.get("run_on_startup", False))
        
        lang = s.get("language", "ru")
        self.language.setCurrentIndex(0 if lang == "ru" else 1)
        
        self.http_port.setValue(s.get("proxy_port", 10808))
        self.socks_port.setValue(s.get("socks_port", 10809))
        self.allow_lan.setChecked(s.get("allow_lan", False))
        
        mode = s.get("routing_mode", "proxy")
        for i in range(self.routing_mode.count()):
            if self.routing_mode.itemData(i) == mode:
                self.routing_mode.setCurrentIndex(i)
                break
        
        self.dns_primary.setText(s.get("dns_primary", "1.1.1.1"))
        self.dns_secondary.setText(s.get("dns_secondary", "8.8.8.8"))

    def _save(self):
        s = self._settings
        s.set("auto_connect", self.auto_connect.isChecked())
        s.set("run_on_startup", self.run_startup.isChecked())
        s.set("language", "ru" if self.language.currentIndex() == 0 else "en")
        s.set("proxy_port", self.http_port.value())
        s.set("socks_port", self.socks_port.value())
        s.set("allow_lan", self.allow_lan.isChecked())
        s.set("routing_mode", self.routing_mode.currentData())
        s.set("dns_primary", self.dns_primary.text().strip() or "1.1.1.1")
        s.set("dns_secondary", self.dns_secondary.text().strip() or "8.8.8.8")
        
        # Windows startup
        self._update_startup(s.get("run_on_startup", False))
        
        self.settings_changed.emit()
        self.accept()

    def _update_startup(self, enable: bool):
        """Add/remove from Windows startup"""
        try:
            import winreg
            import sys
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            if enable:
                exe_path = sys.executable
                winreg.SetValueEx(key, "NexiaVPN", 0, winreg.REG_SZ,
                                  f'"{exe_path}" "{__file__}"')
            else:
                try:
                    winreg.DeleteValue(key, "NexiaVPN")
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
        except Exception:
            pass  # Non-Windows or permission issue
