"""
Server Storage - stores servers with encrypted sensitive fields
"""
import json
import os
import base64
import hashlib
from typing import List, Optional
from core.link_parser import ServerConfig
from utils.logger import get_logger

logger = get_logger()

STORAGE_FILE = os.path.join("config", "servers.json")
SETTINGS_FILE = os.path.join("config", "settings.json")

# Simple obfuscation key (not cryptographic, just prevents casual reading)
_OBFUSCATION_KEY = b"NexiaVPN2024SecureStorage"


def _obfuscate(data: str) -> str:
    key = _OBFUSCATION_KEY
    encoded = data.encode("utf-8")
    result = bytes(b ^ key[i % len(key)] for i, b in enumerate(encoded))
    return base64.b64encode(result).decode("ascii")


def _deobfuscate(data: str) -> str:
    key = _OBFUSCATION_KEY
    decoded = base64.b64decode(data.encode("ascii"))
    result = bytes(b ^ key[i % len(key)] for i, b in enumerate(decoded))
    return result.decode("utf-8")


class ServerStorage:
    def __init__(self):
        os.makedirs("config", exist_ok=True)
        self._servers: List[dict] = []
        self._load()

    def _load(self):
        if os.path.exists(STORAGE_FILE):
            try:
                with open(STORAGE_FILE, "r", encoding="utf-8") as f:
                    self._servers = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load servers: {e}")
                self._servers = []

    def _save(self):
        try:
            with open(STORAGE_FILE, "w", encoding="utf-8") as f:
                json.dump(self._servers, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save servers: {e}")

    def add_server(self, cfg: ServerConfig) -> str:
        import uuid
        server_id = str(uuid.uuid4())
        entry = {
            "id": server_id,
            "name": cfg.name,
            "protocol": cfg.protocol,
            "address": cfg.address,
            "port": cfg.port,
            "network": cfg.network,
            "tls": cfg.tls,
            "country": cfg.country,
            # Obfuscated sensitive data
            "_link": _obfuscate(cfg.raw_link),
        }
        self._servers.append(entry)
        self._save()
        logger.info(f"Server added: {cfg.name} ({cfg.protocol})")
        return server_id

    def remove_server(self, server_id: str) -> bool:
        original_len = len(self._servers)
        self._servers = [s for s in self._servers if s["id"] != server_id]
        if len(self._servers) < original_len:
            self._save()
            logger.info(f"Server removed: {server_id}")
            return True
        return False

    def rename_server(self, server_id: str, new_name: str) -> bool:
        for server in self._servers:
            if server["id"] == server_id:
                server["name"] = new_name
                self._save()
                return True
        return False

    def get_all(self) -> List[dict]:
        return list(self._servers)

    def get_server_link(self, server_id: str) -> Optional[str]:
        for server in self._servers:
            if server["id"] == server_id:
                try:
                    return _deobfuscate(server["_link"])
                except Exception:
                    return None
        return None

    def get_server_config(self, server_id: str) -> Optional[ServerConfig]:
        from core.link_parser import LinkParser
        link = self.get_server_link(server_id)
        if link:
            return LinkParser.parse(link)
        return None

    def update_country(self, server_id: str, country: str):
        for server in self._servers:
            if server["id"] == server_id:
                server["country"] = country
                self._save()
                return


class SettingsStorage:
    DEFAULTS = {
        "auto_connect": False,
        "run_on_startup": False,
        "routing_mode": "proxy",   # proxy / global / bypass_cn
        "proxy_port": 10808,
        "socks_port": 10809,
        "dns_primary": "1.1.1.1",
        "dns_secondary": "8.8.8.8",
        "language": "ru",
        "last_server_id": None,
        "allow_lan": False,
    }

    def __init__(self):
        os.makedirs("config", exist_ok=True)
        self._data = dict(self.DEFAULTS)
        self._load()

    def _load(self):
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                    self._data.update(saved)
            except Exception as e:
                logger.error(f"Failed to load settings: {e}")

    def save(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def get(self, key: str, default=None):
        return self._data.get(key, default if default is not None else self.DEFAULTS.get(key))

    def set(self, key: str, value):
        self._data[key] = value
        self.save()

    def all(self) -> dict:
        return dict(self._data)
