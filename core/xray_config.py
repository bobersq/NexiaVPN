"""
Xray-core configuration generator
Supports: VLESS, VMess, Trojan, Shadowsocks
"""
import json
import os
from core.link_parser import ServerConfig
from core.server_storage import SettingsStorage


def generate_xray_config(cfg: ServerConfig, settings: SettingsStorage) -> dict:
    """Generate full xray-core JSON config from server config"""
    
    proxy_port = settings.get("proxy_port", 10808)
    socks_port = settings.get("socks_port", 10809)
    dns_primary = settings.get("dns_primary", "1.1.1.1")
    dns_secondary = settings.get("dns_secondary", "8.8.8.8")
    routing_mode = settings.get("routing_mode", "proxy")
    allow_lan = settings.get("allow_lan", False)
    
    listen_addr = "0.0.0.0" if allow_lan else "127.0.0.1"
    
    config = {
        "log": {
            "loglevel": "warning",
            "access": "",
            "error": os.path.join("logs", "xray_error.log")
        },
        "dns": _build_dns(dns_primary, dns_secondary),
        "inbounds": [
            {
                "tag": "http-in",
                "port": proxy_port,
                "listen": listen_addr,
                "protocol": "http",
                "settings": {"timeout": 300, "allowTransparent": False},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]}
            },
            {
                "tag": "socks-in",
                "port": socks_port,
                "listen": listen_addr,
                "protocol": "socks",
                "settings": {"auth": "noauth", "udp": True},
                "sniffing": {"enabled": True, "destOverride": ["http", "tls", "quic"]}
            }
        ],
        "outbounds": [
            _build_outbound(cfg),
            {"tag": "direct", "protocol": "freedom", "settings": {}},
            {"tag": "block", "protocol": "blackhole", "settings": {"response": {"type": "http"}}}
        ],
        "routing": _build_routing(routing_mode)
    }
    
    return config


def _build_dns(primary: str, secondary: str) -> dict:
    return {
        "servers": [
            {"address": primary, "domains": ["geosite:google", "geosite:github"]},
            {"address": secondary},
            "localhost"
        ]
    }


def _build_outbound(cfg: ServerConfig) -> dict:
    if cfg.protocol == "vless":
        return _vless_outbound(cfg)
    elif cfg.protocol == "vmess":
        return _vmess_outbound(cfg)
    elif cfg.protocol == "trojan":
        return _trojan_outbound(cfg)
    elif cfg.protocol == "ss":
        return _ss_outbound(cfg)
    else:
        raise ValueError(f"Unsupported protocol: {cfg.protocol}")


def _stream_settings(cfg: ServerConfig) -> dict:
    stream = {"network": cfg.network}
    
    # Network-specific settings
    if cfg.network == "ws":
        stream["wsSettings"] = {
            "path": cfg.path or "/",
            "headers": {"Host": cfg.host} if cfg.host else {}
        }
    elif cfg.network == "grpc":
        stream["grpcSettings"] = {
            "serviceName": cfg.path or "",
            "multiMode": False
        }
    elif cfg.network == "h2":
        stream["httpSettings"] = {
            "path": cfg.path or "/",
            "host": [cfg.host] if cfg.host else []
        }
    elif cfg.network == "quic":
        stream["quicSettings"] = {
            "security": "none",
            "header": {"type": "none"}
        }
    
    # TLS settings
    security = cfg.extra.get("security", "none") if cfg.extra else "none"
    
    if security == "reality":
        stream["security"] = "reality"
        stream["realitySettings"] = {
            "serverName": cfg.sni or cfg.address,
            "fingerprint": cfg.fingerprint or "chrome",
            "shortId": cfg.reality_short_id or "",
            "publicKey": cfg.reality_public_key or "",
            "spiderX": "/"
        }
    elif security == "tls" or cfg.tls:
        stream["security"] = "tls"
        tls_settings = {}
        if cfg.sni:
            tls_settings["serverName"] = cfg.sni
        if cfg.fingerprint:
            tls_settings["fingerprint"] = cfg.fingerprint
        tls_settings["allowInsecure"] = False
        stream["tlsSettings"] = tls_settings
    
    return stream


def _vless_outbound(cfg: ServerConfig) -> dict:
    outbound = {
        "tag": "proxy",
        "protocol": "vless",
        "settings": {
            "vnext": [{
                "address": cfg.address,
                "port": cfg.port,
                "users": [{
                    "id": cfg.uuid,
                    "encryption": cfg.encryption or "none",
                    "flow": cfg.flow or ""
                }]
            }]
        },
        "streamSettings": _stream_settings(cfg),
        "mux": {"enabled": False}
    }
    return outbound


def _vmess_outbound(cfg: ServerConfig) -> dict:
    outbound = {
        "tag": "proxy",
        "protocol": "vmess",
        "settings": {
            "vnext": [{
                "address": cfg.address,
                "port": cfg.port,
                "users": [{
                    "id": cfg.uuid,
                    "alterId": cfg.extra.get("aid", 0) if cfg.extra else 0,
                    "security": "auto"
                }]
            }]
        },
        "streamSettings": _stream_settings(cfg),
        "mux": {"enabled": False}
    }
    return outbound


def _trojan_outbound(cfg: ServerConfig) -> dict:
    stream = _stream_settings(cfg)
    # Trojan always needs TLS
    if "security" not in stream or stream.get("security") not in ("tls", "reality"):
        stream["security"] = "tls"
        stream.setdefault("tlsSettings", {})["serverName"] = cfg.sni or cfg.address
    
    outbound = {
        "tag": "proxy",
        "protocol": "trojan",
        "settings": {
            "servers": [{
                "address": cfg.address,
                "port": cfg.port,
                "password": cfg.password,
                "level": 0
            }]
        },
        "streamSettings": stream,
        "mux": {"enabled": False}
    }
    return outbound


def _ss_outbound(cfg: ServerConfig) -> dict:
    outbound = {
        "tag": "proxy",
        "protocol": "shadowsocks",
        "settings": {
            "servers": [{
                "address": cfg.address,
                "port": cfg.port,
                "method": cfg.encryption or "aes-128-gcm",
                "password": cfg.password,
                "uot": False,
                "level": 0
            }]
        },
        "mux": {"enabled": False}
    }
    return outbound


def _build_routing(mode: str) -> dict:
    rules = [
        # Always block ads
        {
            "type": "field",
            "domain": ["geosite:category-ads-all"],
            "outboundTag": "block"
        },
        # Private networks always go direct
        {
            "type": "field",
            "ip": ["geoip:private", "127.0.0.1/32"],
            "outboundTag": "direct"
        }
    ]
    
    if mode == "bypass_cn":
        # Chinese mainland traffic goes direct
        rules.append({
            "type": "field",
            "domain": ["geosite:cn"],
            "outboundTag": "direct"
        })
        rules.append({
            "type": "field",
            "ip": ["geoip:cn"],
            "outboundTag": "direct"
        })
    elif mode == "global":
        # Everything through proxy
        pass
    # else "proxy" - default behavior
    
    return {
        "domainStrategy": "IPIfNonMatch",
        "rules": rules
    }


def save_config(config: dict, path: str = None) -> str:
    if path is None:
        path = os.path.join("config", "xray_config.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    return path
