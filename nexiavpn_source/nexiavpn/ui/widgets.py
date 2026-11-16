"""
Custom UI Widgets for NexiaVPN
"""
import math
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QSizePolicy, QMenu, QListWidgetItem
)
from PySide6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
    Property, Signal, QRect, QPointF, QRectF, QSize
)
from PySide6.QtGui import (
    QPainter, QColor, QLinearGradient, QRadialGradient,
    QPen, QBrush, QFont, QFontMetrics, QPainterPath,
    QConicalGradient
)


class ConnectButton(QWidget):
    """Animated connect/disconnect button with pulsing ring effect"""
    
    clicked = Signal()
    
    IDLE_COLOR = QColor(99, 102, 241)       # indigo-500
    CONNECTED_COLOR = QColor(34, 197, 94)    # green-500
    CONNECTING_COLOR = QColor(251, 191, 36)  # amber-400
    ERROR_COLOR = QColor(239, 68, 68)        # red-500
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(200, 200)
        self.setCursor(Qt.PointingHandCursor)
        
        self._state = "idle"  # idle, connecting, connected, error
        self._pulse_radius = 0.0
        self._pulse_alpha = 0
        self._rotation = 0.0
        self._glow_intensity = 0.0
        self._glow_direction = 1
        
        # Pulse animation
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._animate_pulse)
        self._pulse_timer.start(16)  # ~60fps
        
    def set_state(self, state: str):
        """state: idle, connecting, connected, error"""
        self._state = state
        self._pulse_radius = 0
        self.update()
    
    def _animate_pulse(self):
        if self._state == "connecting":
            self._rotation = (self._rotation + 3) % 360
        elif self._state == "connected":
            self._pulse_radius = (self._pulse_radius + 0.5) % 100
            self._glow_intensity += 0.03 * self._glow_direction
            if self._glow_intensity >= 1.0 or self._glow_intensity <= 0.0:
                self._glow_direction *= -1
        elif self._state == "idle":
            self._glow_intensity += 0.02 * self._glow_direction
            if self._glow_intensity >= 0.6 or self._glow_intensity <= 0.0:
                self._glow_direction *= -1
        self.update()

    def _get_color(self) -> QColor:
        if self._state == "connected": return self.CONNECTED_COLOR
        if self._state == "connecting": return self.CONNECTING_COLOR
        if self._state == "error": return self.ERROR_COLOR
        return self.IDLE_COLOR

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        cx, cy = self.width() / 2, self.height() / 2
        color = self._get_color()
        
        # === Outer glow ring ===
        if self._state in ("connected", "idle"):
            glow_radius = 85 + self._glow_intensity * 10
            glow = QRadialGradient(cx, cy, glow_radius)
            c = QColor(color)
            c.setAlphaF(0.15 * self._glow_intensity)
            glow.setColorAt(0, c)
            glow.setColorAt(1, Qt.transparent)
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(QRectF(cx - glow_radius, cy - glow_radius,
                                       glow_radius * 2, glow_radius * 2))
        
        # === Pulse rings (connected) ===
        if self._state == "connected":
            for i in range(3):
                r = 70 + (self._pulse_radius + i * 33) % 100
                alpha = max(0, int(180 * (1 - r / 100)))
                ring_c = QColor(color)
                ring_c.setAlpha(alpha)
                pen = QPen(ring_c, 1.5)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        
        # === Rotating arc (connecting) ===
        if self._state == "connecting":
            pen = QPen(color, 4)
            pen.setCapStyle(Qt.RoundCap)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            # Draw arc
            start_angle = int(self._rotation * 16)
            span = 100 * 16
            r = 78
            painter.drawArc(QRectF(cx - r, cy - r, r * 2, r * 2), start_angle, span)
            
            # Dashed outer ring
            pen2 = QPen(QColor(color.red(), color.green(), color.blue(), 40), 2)
            pen2.setStyle(Qt.DashLine)
            painter.setPen(pen2)
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        
        # === Background circle ===
        bg_gradient = QRadialGradient(cx, cy, 70)
        bg_dark = QColor(13, 17, 23)
        bg_mid = QColor(20, 27, 45)
        bg_gradient.setColorAt(0, bg_mid)
        bg_gradient.setColorAt(1, bg_dark)
        painter.setBrush(QBrush(bg_gradient))
        
        # Border
        border_color = QColor(color)
        border_color.setAlphaF(0.6)
        painter.setPen(QPen(border_color, 2.5))
        painter.drawEllipse(QRectF(cx - 70, cy - 70, 140, 140))
        
        # === Power icon ===
        icon_color = color if self._state != "idle" else QColor(color.red(), color.green(), color.blue(), 200)
        painter.setPen(QPen(icon_color, 4, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        
        # Power circle arc (270 deg, missing top)
        arc_r = 24
        painter.drawArc(QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2), 50 * 16, 260 * 16)
        
        # Power vertical line
        painter.drawLine(QPointF(cx, cy - arc_r - 10), QPointF(cx, cy - 4))
        
        # === Label ===
        labels = {
            "idle": "CONNECT",
            "connecting": "CONNECTING",
            "connected": "CONNECTED",
            "error": "ERROR"
        }
        label = labels.get(self._state, "CONNECT")
        
        painter.setPen(QColor(255, 255, 255, 220))
        font = QFont("Segoe UI", 9, QFont.Bold)
        font.setLetterSpacing(QFont.AbsoluteSpacing, 2)
        painter.setFont(font)
        painter.drawText(QRectF(cx - 70, cy + 32, 140, 20), Qt.AlignCenter, label)
        
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()

    def sizeHint(self):
        return QSize(200, 200)


class ServerCard(QWidget):
    """Server list item card"""
    
    connect_requested = Signal(str)   # server_id
    rename_requested = Signal(str)
    delete_requested = Signal(str)
    
    def __init__(self, server_id: str, name: str, protocol: str,
                 address: str, country: str = "", ping: int = None,
                 is_active: bool = False, parent=None):
        super().__init__(parent)
        self.server_id = server_id
        self._is_active = is_active
        self._ping = ping
        
        self.setMinimumHeight(72)
        self.setMaximumHeight(72)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)
        
        self._setup_ui(name, protocol, address, country)
        self._update_style()

    def _setup_ui(self, name, protocol, address, country):
        from utils.geo import get_flag, get_country_name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(12)
        
        # Flag / country
        flag = get_flag(country)
        flag_label = QLabel(flag)
        flag_label.setFont(QFont("Segoe UI Emoji", 20))
        flag_label.setFixedWidth(36)
        flag_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(flag_label)
        
        # Server info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        self.name_label = QLabel(name)
        self.name_label.setFont(QFont("Segoe UI", 12, QFont.Medium))
        self.name_label.setStyleSheet("color: #e2e8f0;")
        
        country_name = get_country_name(country) or address
        proto_colors = {
            "vless": "#818cf8", "vmess": "#a78bfa",
            "trojan": "#34d399", "ss": "#fb923c"
        }
        proto_color = proto_colors.get(protocol.lower(), "#94a3b8")
        
        sub_label = QLabel(f'<span style="color:{proto_color}; font-weight:600">{protocol.upper()}</span>'
                           f' · {country_name}')
        sub_label.setFont(QFont("Segoe UI", 10))
        sub_label.setStyleSheet("color: #64748b;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(sub_label)
        layout.addLayout(info_layout, stretch=1)
        
        # Ping badge
        self.ping_label = QLabel()
        self._update_ping_label()
        self.ping_label.setFont(QFont("Segoe UI", 10, QFont.Medium))
        self.ping_label.setFixedWidth(60)
        self.ping_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        layout.addWidget(self.ping_label)
        
        # Active indicator
        self.active_dot = QLabel("●")
        self.active_dot.setFont(QFont("Segoe UI", 8))
        self.active_dot.setFixedWidth(16)
        layout.addWidget(self.active_dot)
        
    def _update_ping_label(self):
        if self._ping is None:
            self.ping_label.setText("— ms")
            self.ping_label.setStyleSheet("color: #4a5568;")
        elif self._ping < 100:
            self.ping_label.setText(f"{self._ping} ms")
            self.ping_label.setStyleSheet("color: #34d399;")
        elif self._ping < 200:
            self.ping_label.setText(f"{self._ping} ms")
            self.ping_label.setStyleSheet("color: #fbbf24;")
        else:
            self.ping_label.setText(f"{self._ping} ms")
            self.ping_label.setStyleSheet("color: #f87171;")

    def set_ping(self, ping):
        self._ping = ping
        self._update_ping_label()

    def set_active(self, active: bool):
        self._is_active = active
        self._update_style()

    def _update_style(self):
        if self._is_active:
            self.setStyleSheet("""
                ServerCard {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(99,102,241,0.15), stop:1 rgba(139,92,246,0.08));
                    border: 1px solid rgba(99,102,241,0.4);
                    border-radius: 12px;
                }
                ServerCard:hover {
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                        stop:0 rgba(99,102,241,0.22), stop:1 rgba(139,92,246,0.14));
                }
            """)
            self.active_dot.setStyleSheet("color: #6366f1;")
        else:
            self.setStyleSheet("""
                ServerCard {
                    background: rgba(19, 25, 41, 0.6);
                    border: 1px solid rgba(45, 63, 94, 0.5);
                    border-radius: 12px;
                }
                ServerCard:hover {
                    background: rgba(30, 37, 59, 0.8);
                    border-color: rgba(99, 102, 241, 0.3);
                }
            """)
            self.active_dot.setStyleSheet("color: transparent;")

    def mouseDoubleClickEvent(self, event):
        self.connect_requested.emit(self.server_id)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu { background: #131929; border: 1px solid #2d3f5e; border-radius: 8px; padding: 4px; }
            QMenu::item { padding: 8px 16px; color: #e2e8f0; border-radius: 4px; }
            QMenu::item:selected { background: #2d3f5e; }
        """)
        
        connect_action = menu.addAction("⚡  Подключиться")
        rename_action = menu.addAction("✏️  Переименовать")
        menu.addSeparator()
        delete_action = menu.addAction("🗑️  Удалить")
        
        action = menu.exec(event.globalPos())
        if action == connect_action:
            self.connect_requested.emit(self.server_id)
        elif action == rename_action:
            self.rename_requested.emit(self.server_id)
        elif action == delete_action:
            self.delete_requested.emit(self.server_id)


class StatusBar(QWidget):
    """Bottom status bar showing connection info"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(44)
        self.setStyleSheet("background: rgba(10, 14, 26, 0.95); border-top: 1px solid #1e2535;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 0, 20, 0)
        
        self.status_dot = QLabel("●")
        self.status_dot.setFont(QFont("Segoe UI", 10))
        self.status_label = QLabel("Не подключено")
        self.status_label.setStyleSheet("color: #64748b; font-size: 12px;")
        
        layout.addWidget(self.status_dot)
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        self.ping_label = QLabel()
        self.ping_label.setStyleSheet("color: #64748b; font-size: 12px;")
        layout.addWidget(self.ping_label)
        
        self.proxy_label = QLabel()
        self.proxy_label.setStyleSheet("color: #4a5568; font-size: 11px;")
        layout.addWidget(self.proxy_label)
        
        self.set_disconnected()

    def set_connected(self, server_name: str, proxy_port: int):
        self.status_dot.setStyleSheet("color: #22c55e; font-size: 10px;")
        self.status_label.setText(f"Подключено · {server_name}")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.proxy_label.setText(f"HTTP: 127.0.0.1:{proxy_port}")

    def set_connecting(self):
        self.status_dot.setStyleSheet("color: #fbbf24; font-size: 10px;")
        self.status_label.setText("Подключение...")
        self.status_label.setStyleSheet("color: #94a3b8; font-size: 12px;")
        self.ping_label.setText("")
        self.proxy_label.setText("")

    def set_disconnected(self):
        self.status_dot.setStyleSheet("color: #ef4444; font-size: 10px;")
        self.status_label.setText("Не подключено")
        self.status_label.setStyleSheet("color: #64748b; font-size: 12px;")
        self.ping_label.setText("")
        self.proxy_label.setText("")

    def set_error(self, msg: str):
        self.status_dot.setStyleSheet("color: #ef4444; font-size: 10px;")
        self.status_label.setText(f"Ошибка: {msg}")
        self.status_label.setStyleSheet("color: #ef4444; font-size: 12px;")

    def set_ping(self, ping):
        if ping is not None:
            self.ping_label.setText(f"Пинг: {ping} мс")
            if ping < 100:
                self.ping_label.setStyleSheet("color: #34d399; font-size: 12px;")
            elif ping < 200:
                self.ping_label.setStyleSheet("color: #fbbf24; font-size: 12px;")
            else:
                self.ping_label.setStyleSheet("color: #f87171; font-size: 12px;")
        else:
            self.ping_label.setText("")


class GlassPanel(QFrame):
    """Glassmorphism panel"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            GlassPanel {
                background: rgba(13, 20, 38, 0.7);
                border: 1px solid rgba(99, 102, 241, 0.15);
                border-radius: 16px;
            }
        """)
