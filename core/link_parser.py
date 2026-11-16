"""
VPN Link Parser - supports vless://, vmess://, trojan://, ss://
"""
import base64
import json
import re
import urllib.parse
from dataclasses import dataclass, field
from typing import Optional
from utils.logger import get_logger

logger = get_logger()


@dataclass
class ServerConfig:
    protocol: str           # vless, vmess, trojan, ss
    address: str
    port: int
    name: str = ""
    uuid: str = ""
    password: str = ""
    network: str = "tcp"
    tls: bool = False
    sni: str = ""
    path: str = ""
    host: str = ""
    encryption: str = "none"
    flow: str = ""
    fingerprint: str = ""
    reality_public_key: str = ""
    reality_short_id: str = ""
    country: str = ""
    raw_link: str = ""      # stored encrypted, not logged
    extra: dict = field(default_factory=dict)

    def display_address(self):
        return f"{self.address}:{self.port}"


class LinkParser:
    
    @staticmethod
    def parse(link: str) -> Optional[ServerConfig]:
        link = link.strip()
        try:
            if link.startswith("vless://"):
                return LinkParser._parse_vless(link)
            elif link.startswith("vmess://"):
                return LinkParser._parse_vmess(link)
            elif link.startswith("trojan://"):
                return LinkParser._parse_trojan(link)
            elif link.startswith("ss://"):
                return LinkParser._parse_shadowsocks(link)
            else:
                logger.warning("Unknown protocol in link")
                return None
        except Exception as e:
            logger.error(f"Link parsing error: {e}")
            return None

    @staticmethod
    def _parse_vless(link: str) -> ServerConfig:
        # vless://uuid@address:port?params#name
        parsed = urllib.parse.urlparse(link)
        uuid = parsed.username or ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        
        params = dict(urllib.parse.parse_qsl(parsed.query))
        name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else address
        
        tls_type = params.get("security", "none")
        network = params.get("type", "tcp")
        
        cfg = ServerConfig(
            protocol="vless",
            address=address,
            port=port,
            uuid=uuid,
            name=name,
            network=network,
            tls=(tls_type in ("tls", "reality", "xtls")),
            sni=params.get("sni", params.get("peer", "")),
            path=params.get("path", ""),
            host=params.get("host", ""),
            flow=params.get("flow", ""),
            fingerprint=params.get("fp", ""),
            reality_public_key=params.get("pbk", ""),
            reality_short_id=params.get("sid", ""),
            encryption=params.get("encryption", "none"),
            raw_link=link,
            extra={"security": tls_type}
        )
        return cfg

    @staticmethod
    def _parse_vmess(link: str) -> ServerConfig:
        # vmess://base64(json)
        b64 = link[8:]
        # Fix padding
        b64 += "=" * (4 - len(b64) % 4)
        try:
            decoded = base64.b64decode(b64).decode("utf-8")
            data = json.loads(decoded)
        except Exception:
            raise ValueError("Invalid VMess base64 data")
        
        network = data.get("net", "tcp")
        tls = data.get("tls", "") == "tls"
        
        cfg = ServerConfig(
            protocol="vmess",
            address=data.get("add", ""),
            port=int(data.get("port", 443)),
            uuid=data.get("id", ""),
            name=data.get("ps", data.get("add", "")),
            network=network,
            tls=tls,
            sni=data.get("sni", data.get("host", "")),
            path=data.get("path", ""),
            host=data.get("host", ""),
            raw_link=link,
            extra={"aid": data.get("aid", 0), "v": data.get("v", "2")}
        )
        return cfg

    @staticmethod
    def _parse_trojan(link: str) -> ServerConfig:
        # trojan://password@address:port?params#name
        parsed = urllib.parse.urlparse(link)
        password = parsed.username or ""
        address = parsed.hostname or ""
        port = parsed.port or 443
        
        params = dict(urllib.parse.parse_qsl(parsed.query))
        name = urllib.parse.unquote(parsed.fragment) if parsed.fragment else address
        
        cfg = ServerConfig(
            protocol="trojan",
            address=address,
            port=port,
            password=password,
            name=name,
            network=params.get("type", "tcp"),
            tls=True,  # Trojan always uses TLS
            sni=params.get("sni", address),
            path=params.get("path", ""),
            host=params.get("host", ""),
            fingerprint=params.get("fp", ""),
            raw_link=link,
            extra={}
        )
        return cfg

    @staticmethod
    def _parse_shadowsocks(link: str) -> ServerConfig:
        # ss://BASE64(method:password)@address:port#name
        # or ss://BASE64(method:password@address:port)#name
        
        link_no_prefix = link[5:]
        
        # Split fragment
        name = ""
        if "#" in link_no_prefix:
            link_no_prefix, frag = link_no_prefix.rsplit("#", 1)
            name = urllib.parse.unquote(frag)
        
        # Try new format first: ss://base64@host:port
        if "@" in link_no_prefix:
            userinfo_b64, hostinfo = link_no_prefix.rsplit("@", 1)
            # Decode userinfo
            padding = 4 - len(userinfo_b64) % 4
            userinfo_b64 += "=" * padding
            try:
                userinfo = base64.b64decode(userinfo_b64).decode("utf-8")
                method, password = userinfo.split(":", 1)
            except Exception:
                method = userinfo_b64
                password = ""
            
            if ":" in hostinfo:
                address, port_str = hostinfo.rsplit(":", 1)
                port = int(port_str)
            else:
                address = hostinfo
                port = 8388
        else:
            # Old format: ss://base64(method:password@host:port)
            padding = 4 - len(link_no_prefix) % 4
            link_no_prefix += "=" * padding
            decoded = base64.b64decode(link_no_prefix).decode("utf-8")
            
            # method:password@host:port
            at_idx = decoded.rfind("@")
            userinfo = decoded[:at_idx]
            hostinfo = decoded[at_idx+1:]
            
            method, password = userinfo.split(":", 1)
            address, port_str = hostinfo.rsplit(":", 1)
            port = int(port_str)
        
        if not name:
            name = address
        
        cfg = ServerConfig(
            protocol="ss",
            address=address,
            port=port,
            password=password,
            name=name,
            encryption=method,
            raw_link=link,
            extra={}
        )
        return cfg

    @staticmethod
    def detect_protocol(link: str) -> Optional[str]:
        for proto in ("vless", "vmess", "trojan", "ss"):
            if link.startswith(f"{proto}://"):
                return proto
        return None
