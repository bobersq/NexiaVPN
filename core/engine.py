"""
Xray-core Engine Manager
Handles process lifecycle, connection status, ping measurement
"""
import os
import subprocess
import threading
import time
import socket
import json
import urllib.request
import urllib.error
from enum import Enum
from typing import Optional, Callable

from core.link_parser import ServerConfig
from core.xray_config import generate_xray_config, save_config
from core.server_storage import SettingsStorage
from utils.logger import get_logger

logger = get_logger()

XRAY_EXE = os.path.join("bin", "xray.exe")
CONFIG_PATH = os.path.join("config", "xray_config.json")


class ConnectionState(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class XrayEngine:
    def __init__(self):
        self._process: Optional[subprocess.Popen] = None
        self._state = ConnectionState.DISCONNECTED
        self._current_server: Optional[ServerConfig] = None
        self._settings = SettingsStorage()
        self._ping_ms: Optional[int] = None
        self._error_msg: str = ""
        
        # Callbacks
        self.on_state_change: Optional[Callable] = None
        self.on_ping_update: Optional[Callable] = None
        self.on_log: Optional[Callable] = None
        
        self._ping_thread: Optional[threading.Thread] = None
        self._stop_ping = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None

    @property
    def state(self) -> ConnectionState:
        return self._state

    @property
    def ping(self) -> Optional[int]:
        return self._ping_ms

    @property
    def error_message(self) -> str:
        return self._error_msg

    @property
    def is_connected(self) -> bool:
        return self._state == ConnectionState.CONNECTED

    def _set_state(self, state: ConnectionState, error: str = ""):
        self._state = state
        self._error_msg = error
        logger.info(f"Engine state: {state.value}")
        if self.on_state_change:
            self.on_state_change(state, error)

    def connect(self, server: ServerConfig) -> bool:
        if self._state in (ConnectionState.CONNECTED, ConnectionState.CONNECTING):
            self.disconnect()
            time.sleep(0.5)
        
        self._current_server = server
        self._set_state(ConnectionState.CONNECTING)
        
        # Run in thread to not block UI
        thread = threading.Thread(target=self._do_connect, daemon=True)
        thread.start()
        return True

    def _do_connect(self):
        try:
            # 1. Generate xray config
            config = generate_xray_config(self._current_server, self._settings)
            config_path = save_config(config, CONFIG_PATH)
            
            # 2. Verify xray binary exists
            if not os.path.exists(XRAY_EXE):
                self._set_state(ConnectionState.ERROR, "Xray не найден. Переустановите приложение.")
                return
            
            # 3. Start xray process
            logger.info(f"Starting xray for {self._current_server.address}:{self._current_server.port}")
            
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
            
            self._process = subprocess.Popen(
                [XRAY_EXE, "-config", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            
            # 4. Wait for xray to initialize (max 5 sec)
            time.sleep(1.5)
            
            # Check if process is still running
            if self._process.poll() is not None:
                stderr = self._process.stderr.read().decode("utf-8", errors="replace")
                self._set_state(ConnectionState.ERROR, f"Xray завершился: {stderr[:200]}")
                return
            
            # 5. Verify connection works through proxy
            if not self._verify_connectivity():
                self._kill_process()
                self._set_state(ConnectionState.ERROR, "Не удалось подключиться к серверу. Проверьте настройки.")
                return
            
            self._set_state(ConnectionState.CONNECTED)
            
            # 6. Start monitoring
            self._stop_ping.clear()
            self._ping_thread = threading.Thread(target=self._ping_loop, daemon=True)
            self._ping_thread.start()
            
            self._monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            self._monitor_thread.start()
            
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self._kill_process()
            self._set_state(ConnectionState.ERROR, f"Ошибка подключения: {str(e)}")

    def _verify_connectivity(self) -> bool:
        """Verify that xray proxy is working"""
        proxy_port = self._settings.get("proxy_port", 10808)
        
        # Try to connect through the HTTP proxy
        for attempt in range(3):
            try:
                proxy_handler = urllib.request.ProxyHandler({
                    "http": f"http://127.0.0.1:{proxy_port}",
                    "https": f"http://127.0.0.1:{proxy_port}"
                })
                opener = urllib.request.build_opener(proxy_handler)
                opener.addheaders = [("User-Agent", "Mozilla/5.0")]
                
                # Try a lightweight connectivity check
                response = opener.open("http://cp.cloudflare.com/", timeout=10)
                if response.getcode() == 200:
                    logger.info("Connectivity verified via proxy")
                    return True
            except Exception as e:
                logger.debug(f"Connectivity check attempt {attempt+1} failed: {e}")
                time.sleep(1)
        
        # Also check if proxy port is accepting connections
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex(("127.0.0.1", proxy_port))
            sock.close()
            if result == 0:
                logger.info("Proxy port is open (partial connectivity)")
                return True
        except Exception:
            pass
        
        return False

    def disconnect(self):
        self._set_state(ConnectionState.DISCONNECTING)
        self._stop_ping.set()
        self._kill_process()
        self._ping_ms = None
        if self.on_ping_update:
            self.on_ping_update(None)
        self._set_state(ConnectionState.DISCONNECTED)

    def _kill_process(self):
        if self._process:
            try:
                self._process.terminate()
                try:
                    self._process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self._process.kill()
            except Exception as e:
                logger.warning(f"Error killing xray: {e}")
            self._process = None

    def _monitor_process(self):
        """Monitor xray process, detect crashes"""
        while self._process and not self._stop_ping.is_set():
            if self._process.poll() is not None:
                if self._state == ConnectionState.CONNECTED:
                    stderr = ""
                    try:
                        stderr = self._process.stderr.read(500).decode("utf-8", errors="replace")
                    except Exception:
                        pass
                    logger.warning(f"Xray process died unexpectedly: {stderr}")
                    self._set_state(ConnectionState.ERROR, "Соединение прервано")
                break
            time.sleep(1)

    def _ping_loop(self):
        """Continuously measure ping through proxy"""
        while not self._stop_ping.is_set():
            ping = self._measure_ping()
            self._ping_ms = ping
            if self.on_ping_update:
                self.on_ping_update(ping)
            self._stop_ping.wait(5)  # Update every 5 seconds

    def _measure_ping(self) -> Optional[int]:
        """Measure RTT through xray proxy"""
        proxy_port = self._settings.get("proxy_port", 10808)
        
        try:
            proxy_handler = urllib.request.ProxyHandler({
                "http": f"http://127.0.0.1:{proxy_port}",
                "https": f"http://127.0.0.1:{proxy_port}"
            })
            opener = urllib.request.build_opener(proxy_handler)
            opener.addheaders = [("User-Agent", "NexiaVPN/1.0")]
            
            start = time.monotonic()
            response = opener.open("http://cp.cloudflare.com/", timeout=8)
            response.read()
            elapsed_ms = int((time.monotonic() - start) * 1000)
            return elapsed_ms
        except Exception:
            return None

    def measure_server_ping(self, server: ServerConfig, callback: Callable):
        """Quick TCP ping to server address:port"""
        def _do_ping():
            try:
                start = time.monotonic()
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((server.address, server.port))
                elapsed_ms = int((time.monotonic() - start) * 1000)
                sock.close()
                if result == 0:
                    callback(elapsed_ms)
                else:
                    callback(None)
            except Exception:
                callback(None)
        
        t = threading.Thread(target=_do_ping, daemon=True)
        t.start()
