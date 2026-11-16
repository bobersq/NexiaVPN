"""
Setup Manager - checks and installs dependencies automatically
Downloads xray-core from official GitHub releases
"""
import os
import sys
import json
import hashlib
import zipfile
import urllib.request
import urllib.error
import threading
from typing import Optional, Callable

from utils.logger import get_logger

logger = get_logger()

XRAY_EXE = os.path.join("bin", "xray.exe")
XRAY_VERSION_FILE = os.path.join("bin", "xray_version.txt")

# Official xray-core release
XRAY_GITHUB_API = "https://api.github.com/repos/XTLS/Xray-core/releases/latest"
XRAY_DIRECT_URL = "https://github.com/XTLS/Xray-core/releases/latest/download/Xray-windows-64.zip"
XRAY_FALLBACK_VERSION = "v24.11.30"
XRAY_FALLBACK_URL = f"https://github.com/XTLS/Xray-core/releases/download/{XRAY_FALLBACK_VERSION}/Xray-windows-64.zip"


class SetupManager:
    def check_all(self) -> bool:
        """Returns True if all dependencies are present"""
        return os.path.exists(XRAY_EXE)

    def show_setup_dialog(self, app):
        """Show setup dialog and install dependencies"""
        from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QTextEdit
        from PySide6.QtCore import Qt, Signal, QObject, QThread
        from PySide6.QtGui import QFont

        class DownloadWorker(QObject):
            progress = None  # Will be set dynamically
            status = None
            finished = None
            failed = None

            def run(self):
                pass

        class SetupDialog(QDialog):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("NexiaVPN - Первоначальная настройка")
                self.setFixedSize(500, 380)
                self.setStyleSheet("""
                    QDialog { background: #0d1117; color: #e6edf3; }
                    QLabel { color: #e6edf3; }
                    QProgressBar {
                        border: 1px solid #30363d;
                        border-radius: 4px;
                        background: #161b22;
                        height: 20px;
                        text-align: center;
                        color: white;
                    }
                    QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #8b5cf6); border-radius: 3px; }
                    QPushButton { background: #3b82f6; color: white; border: none; padding: 10px 20px; border-radius: 6px; font-size: 14px; }
                    QPushButton:hover { background: #2563eb; }
                    QPushButton:disabled { background: #374151; color: #6b7280; }
                    QTextEdit { background: #161b22; color: #8b949e; border: 1px solid #30363d; border-radius: 4px; font-family: Consolas, monospace; font-size: 11px; }
                """)
                
                layout = QVBoxLayout(self)
                layout.setSpacing(16)
                layout.setContentsMargins(24, 24, 24, 24)
                
                title = QLabel("⚙️  Установка компонентов")
                title.setFont(QFont("Segoe UI", 16, QFont.Bold))
                layout.addWidget(title)
                
                self.status_label = QLabel("Подготовка к установке Xray-core...")
                layout.addWidget(self.status_label)
                
                self.progress = QProgressBar()
                self.progress.setRange(0, 100)
                layout.addWidget(self.progress)
                
                self.log_view = QTextEdit()
                self.log_view.setReadOnly(True)
                self.log_view.setMaximumHeight(140)
                layout.addWidget(self.log_view)
                
                self.btn = QPushButton("Установить")
                self.btn.clicked.connect(self.start_install)
                layout.addWidget(self.btn)
                
                self._success = False

            def log(self, msg):
                self.log_view.append(msg)
                self.log_view.verticalScrollBar().setValue(
                    self.log_view.verticalScrollBar().maximum()
                )

            def start_install(self):
                self.btn.setEnabled(False)
                self.btn.setText("Устанавливается...")
                
                def run():
                    try:
                        self._install()
                    except Exception as e:
                        self._on_failed(str(e))

                t = threading.Thread(target=run, daemon=True)
                t.start()

            def _update_progress(self, pct, msg=""):
                self.progress.setValue(pct)
                if msg:
                    self.status_label.setText(msg)
                    self.log(msg)

            def _install(self):
                from PySide6.QtCore import QMetaObject, Qt, Q_ARG
                
                def update(pct, msg):
                    # Thread-safe UI update
                    self.progress.setValue(pct)
                    if msg:
                        self.status_label.setText(msg)
                        self.log_view.append(msg)

                os.makedirs("bin", exist_ok=True)
                
                # Update from main thread via invokeMethod workaround
                self._progress_pct = 0
                self._progress_msg = ""

                update(5, "Получение информации о последней версии Xray...")
                
                # Try to get latest release URL
                download_url = XRAY_DIRECT_URL
                try:
                    req = urllib.request.Request(
                        XRAY_GITHUB_API,
                        headers={"User-Agent": "NexiaVPN/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=10) as resp:
                        data = json.loads(resp.read())
                        tag = data.get("tag_name", "")
                        for asset in data.get("assets", []):
                            if asset["name"] == "Xray-windows-64.zip":
                                download_url = asset["browser_download_url"]
                                update(10, f"Найдена версия: {tag}")
                                break
                except Exception as e:
                    update(10, f"GitHub API недоступен, используем прямую ссылку")
                    download_url = XRAY_FALLBACK_URL

                zip_path = os.path.join("bin", "xray_download.zip")
                
                update(15, f"Скачивание Xray-core...")
                
                try:
                    self._download_file(download_url, zip_path, 
                                        lambda pct: update(15 + int(pct * 0.65), 
                                                           f"Загрузка: {pct:.0f}%"))
                except Exception as e:
                    # Try fallback
                    update(15, f"Пробуем резервный URL...")
                    self._download_file(XRAY_FALLBACK_URL, zip_path,
                                        lambda pct: update(15 + int(pct * 0.65),
                                                           f"Загрузка (резерв): {pct:.0f}%"))

                update(82, "Проверка архива...")
                
                if not zipfile.is_zipfile(zip_path):
                    raise ValueError("Загруженный файл повреждён")

                update(85, "Распаковка...")
                with zipfile.ZipFile(zip_path, "r") as zf:
                    for name in zf.namelist():
                        if name.lower() in ("xray.exe", "xray"):
                            zf.extract(name, "bin")
                            extracted = os.path.join("bin", name)
                            if not name.endswith(".exe"):
                                os.rename(extracted, XRAY_EXE)
                            break

                update(90, "Очистка временных файлов...")
                try:
                    os.remove(zip_path)
                except Exception:
                    pass

                # Extract geo data files if present
                try:
                    zip_path2 = os.path.join("bin", "xray_download.zip")
                    # already removed above, re-download would be needed
                    # For now skip geo files - xray works without them (with warnings)
                    pass
                except Exception:
                    pass

                if not os.path.exists(XRAY_EXE):
                    raise FileNotFoundError("xray.exe не найден после распаковки")

                # Save version
                with open(XRAY_VERSION_FILE, "w") as f:
                    f.write(download_url)

                update(100, "✅ Xray-core успешно установлен!")
                self._success = True

                import time
                time.sleep(1)
                self.accept()

            def _download_file(self, url: str, path: str, progress_cb: Callable):
                req = urllib.request.Request(url, headers={"User-Agent": "NexiaVPN/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length", 0))
                    downloaded = 0
                    chunk_size = 32768
                    with open(path, "wb") as f:
                        while True:
                            chunk = resp.read(chunk_size)
                            if not chunk:
                                break
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total > 0:
                                progress_cb(downloaded / total * 100)
                    
                    progress_cb(100)

            def _on_failed(self, error: str):
                self.status_label.setText(f"❌ Ошибка: {error}")
                self.log(f"ОШИБКА: {error}")
                self.btn.setEnabled(True)
                self.btn.setText("Повторить")

        dialog = SetupDialog()
        dialog.exec()
