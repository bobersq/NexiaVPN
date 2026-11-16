"""
Add Server Dialog - paste VPN links
"""
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QPushButton, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QColor

from core.link_parser import LinkParser, ServerConfig
from utils.logger import get_logger

logger = get_logger()


class AddServerDialog(QDialog):
    server_added = Signal(object)  # ServerConfig
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Добавить сервер")
        self.setMinimumSize(560, 400)
        self.setModal(True)
        self._parsed_configs = []
        self._setup_ui()

    def _setup_ui(self):
        self.setStyleSheet("""
            QDialog { background: #0a0e1a; }
            QLabel { color: #94a3b8; }
            QTextEdit {
                background: #0d1424;
                border: 1px solid #2d3f5e;
                border-radius: 10px;
                color: #e2e8f0;
                font-family: Consolas, 'Courier New', monospace;
                font-size: 12px;
                padding: 12px;
                line-height: 1.6;
            }
            QTextEdit:focus { border-color: #6366f1; }
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Title
        title = QLabel("➕  Добавить серверы")
        title.setFont(QFont("Segoe UI", 16, QFont.Bold))
        title.setStyleSheet("color: #e2e8f0;")
        layout.addWidget(title)
        
        # Description
        desc = QLabel("Вставьте одну или несколько VPN-ссылок (каждую на новой строке).\n"
                      "Поддерживаются: vless:// · vmess:// · trojan:// · ss://")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Input area
        self.link_input = QTextEdit()
        self.link_input.setPlaceholderText(
            "vless://uuid@server.example.com:443?type=ws&security=tls#My Server\n"
            "vmess://base64encodedconfig...\n"
            "trojan://password@server.example.com:443#Trojan Server\n"
            "ss://base64...@server.example.com:8388#Shadowsocks"
        )
        self.link_input.setMinimumHeight(160)
        self.link_input.textChanged.connect(self._validate)
        layout.addWidget(self.link_input)
        
        # Status area
        self.status_frame = QFrame()
        self.status_frame.setStyleSheet("""
            QFrame { background: #0d1424; border: 1px solid #1e2535; border-radius: 8px; padding: 4px; }
        """)
        status_layout = QVBoxLayout(self.status_frame)
        status_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_label = QLabel("Вставьте ссылки для проверки...")
        self.status_label.setStyleSheet("color: #4a5568; font-size: 12px;")
        status_layout.addWidget(self.status_label)
        layout.addWidget(self.status_frame)
        
        # Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        paste_btn = QPushButton("📋 Вставить из буфера")
        paste_btn.setStyleSheet("""
            QPushButton { background: #1e2535; color: #94a3b8; border: 1px solid #2d3f5e;
                         padding: 10px 16px; border-radius: 8px; font-size: 12px; }
            QPushButton:hover { background: #2d3f5e; color: #e2e8f0; }
        """)
        paste_btn.clicked.connect(self._paste_clipboard)
        
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setStyleSheet("""
            QPushButton { background: #1e2535; color: #94a3b8; border: 1px solid #2d3f5e;
                         padding: 10px 20px; border-radius: 8px; }
            QPushButton:hover { background: #2d3f5e; }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        self.add_btn = QPushButton("Добавить")
        self.add_btn.setEnabled(False)
        self.add_btn.setStyleSheet("""
            QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                             stop:0 #4f46e5, stop:1 #7c3aed);
                         color: white; border: none; padding: 10px 24px;
                         border-radius: 8px; font-weight: bold; }
            QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                             stop:0 #4338ca, stop:1 #6d28d9); }
            QPushButton:disabled { background: #1e2535; color: #4a5568; }
        """)
        self.add_btn.clicked.connect(self._add_servers)
        
        btn_layout.addWidget(paste_btn)
        btn_layout.addSpacing(8)
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(self.add_btn)
        layout.addLayout(btn_layout)

    def _paste_clipboard(self):
        from PySide6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        if text:
            current = self.link_input.toPlainText()
            if current and not current.endswith("\n"):
                self.link_input.setPlainText(current + "\n" + text)
            else:
                self.link_input.setPlainText(current + text)

    def _validate(self):
        text = self.link_input.toPlainText().strip()
        if not text:
            self.status_label.setText("Вставьте ссылки для проверки...")
            self.status_label.setStyleSheet("color: #4a5568; font-size: 12px;")
            self.add_btn.setEnabled(False)
            self._parsed_configs = []
            return
        
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        valid = []
        invalid = []
        
        for line in lines:
            cfg = LinkParser.parse(line)
            if cfg:
                valid.append(cfg)
            elif any(line.startswith(p + "://") for p in ("vless", "vmess", "trojan", "ss")):
                invalid.append(line[:60] + "..." if len(line) > 60 else line)
        
        self._parsed_configs = valid
        
        parts = []
        if valid:
            parts.append(f"<span style='color:#34d399'>✓ {len(valid)} серв. найдено</span>")
        if invalid:
            parts.append(f"<span style='color:#f87171'>✗ {len(invalid)} ошибок</span>")
        
        if valid:
            proto_counts = {}
            for cfg in valid:
                proto_counts[cfg.protocol] = proto_counts.get(cfg.protocol, 0) + 1
            proto_str = " · ".join(f"{p.upper()}: {n}" for p, n in proto_counts.items())
            parts.append(f"<span style='color:#818cf8'>{proto_str}</span>")
        
        self.status_label.setText("  ".join(parts))
        self.add_btn.setEnabled(len(valid) > 0)
        self.add_btn.setText(f"Добавить ({len(valid)})" if len(valid) > 1 else "Добавить")

    def _add_servers(self):
        for cfg in self._parsed_configs:
            self.server_added.emit(cfg)
        self.accept()
