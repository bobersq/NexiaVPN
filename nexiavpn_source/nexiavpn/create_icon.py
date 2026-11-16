"""
Generate NexiaVPN icon (PNG + ICO)
Run this script to create icon files in assets/
"""
import os
import sys

def create_icon():
    os.makedirs("assets", exist_ok=True)
    
    try:
        from PySide6.QtWidgets import QApplication
        from PySide6.QtGui import QPainter, QPixmap, QColor, QLinearGradient, QRadialGradient, QFont, QPen, QBrush, QPainterPath
        from PySide6.QtCore import Qt, QRectF, QPointF
        
        app = QApplication.instance() or QApplication(sys.argv)
        
        size = 256
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        
        cx, cy = size / 2, size / 2
        r = size / 2 - 8
        
        # Outer glow
        glow = QRadialGradient(cx, cy, r + 8)
        glow.setColorAt(0, QColor(99, 102, 241, 60))
        glow.setColorAt(1, QColor(99, 102, 241, 0))
        p.setBrush(QBrush(glow))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(0, 0, size, size))
        
        # Main circle gradient
        grad = QLinearGradient(0, 0, size, size)
        grad.setColorAt(0, QColor(79, 70, 229))   # indigo-600
        grad.setColorAt(0.5, QColor(99, 102, 241)) # indigo-500
        grad.setColorAt(1, QColor(139, 92, 246))   # violet-500
        
        p.setBrush(QBrush(grad))
        p.setPen(QPen(QColor(129, 140, 248, 100), 2))
        p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))
        
        # Inner circle
        inner_grad = QRadialGradient(cx, cy - 20, r * 0.6)
        inner_grad.setColorAt(0, QColor(167, 139, 250, 30))
        inner_grad.setColorAt(1, QColor(0, 0, 0, 0))
        p.setBrush(QBrush(inner_grad))
        p.setPen(Qt.NoPen)
        p.drawEllipse(QRectF(cx - r * 0.9, cy - r * 0.9, r * 1.8, r * 1.8))
        
        # Power icon
        icon_color = QColor(255, 255, 255)
        pen = QPen(icon_color, 14, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin)
        p.setPen(pen)
        
        # Power circle arc
        arc_r = 55
        p.drawArc(QRectF(cx - arc_r, cy - arc_r, arc_r * 2, arc_r * 2), 50 * 16, 260 * 16)
        
        # Vertical line
        p.drawLine(QPointF(cx, cy - arc_r - 20), QPointF(cx, cy - 10))
        
        p.end()
        
        # Save PNG
        png_path = os.path.join("assets", "icon.png")
        pix.save(png_path, "PNG")
        print(f"[OK] Иконка создана: {png_path}")
        
        # Save multiple sizes for ICO
        try:
            from PIL import Image
            import io
            
            images = []
            for sz in (16, 32, 48, 64, 128, 256):
                small = pix.scaled(sz, sz, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                buf = small.toImage()
                # Convert to PIL
                ptr = buf.bits()
                ptr.setsize(buf.byteCount())
                img = Image.frombuffer("RGBA", (sz, sz), bytes(ptr), "raw", "BGRA", 0, 1)
                images.append(img)
            
            ico_path = os.path.join("assets", "icon.ico")
            images[0].save(ico_path, format="ICO", sizes=[(s, s) for s in (16,32,48,64,128,256)])
            print(f"[OK] ICO создан: {ico_path}")
        except ImportError:
            print("[INFO] Pillow не установлен, ICO не создан (нужен только для EXE-сборки)")
        
        return True
        
    except ImportError as e:
        print(f"[ОШИБКА] PySide6 не установлен: {e}")
        return False
    except Exception as e:
        print(f"[ОШИБКА] {e}")
        return False


if __name__ == "__main__":
    create_icon()
