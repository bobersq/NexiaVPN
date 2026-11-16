"""
GeoIP lookup for server country detection
"""
import urllib.request
import json
import threading
from typing import Optional, Callable
from utils.logger import get_logger

logger = get_logger()

# Country code to flag emoji + name
COUNTRY_MAP = {
    "US": ("🇺🇸", "США"), "DE": ("🇩🇪", "Германия"), "NL": ("🇳🇱", "Нидерланды"),
    "GB": ("🇬🇧", "Великобритания"), "FR": ("🇫🇷", "Франция"), "JP": ("🇯🇵", "Япония"),
    "SG": ("🇸🇬", "Сингапур"), "KR": ("🇰🇷", "Корея"), "HK": ("🇭🇰", "Гонконг"),
    "RU": ("🇷🇺", "Россия"), "AU": ("🇦🇺", "Австралия"), "CA": ("🇨🇦", "Канада"),
    "CH": ("🇨🇭", "Швейцария"), "FI": ("🇫🇮", "Финляндия"), "SE": ("🇸🇪", "Швеция"),
    "NO": ("🇳🇴", "Норвегия"), "PL": ("🇵🇱", "Польша"), "CZ": ("🇨🇿", "Чехия"),
    "TR": ("🇹🇷", "Турция"), "UA": ("🇺🇦", "Украина"), "AT": ("🇦🇹", "Австрия"),
    "IT": ("🇮🇹", "Италия"), "ES": ("🇪🇸", "Испания"), "BR": ("🇧🇷", "Бразилия"),
    "IN": ("🇮🇳", "Индия"), "CN": ("🇨🇳", "Китай"), "TW": ("🇹🇼", "Тайвань"),
    "VN": ("🇻🇳", "Вьетнам"), "TH": ("🇹🇭", "Таиланд"), "MY": ("🇲🇾", "Малайзия"),
    "ID": ("🇮🇩", "Индонезия"), "PH": ("🇵🇭", "Филиппины"), "LU": ("🇱🇺", "Люксембург"),
    "BE": ("🇧🇪", "Бельгия"), "DK": ("🇩🇰", "Дания"), "RO": ("🇷🇴", "Румыния"),
    "BG": ("🇧🇬", "Болгария"), "LV": ("🇱🇻", "Латвия"), "LT": ("🇱🇹", "Литва"),
    "EE": ("🇪🇪", "Эстония"), "GE": ("🇬🇪", "Грузия"), "AZ": ("🇦🇿", "Азербайджан"),
    "KZ": ("🇰🇿", "Казахстан"), "UZ": ("🇺🇿", "Узбекистан"), "IL": ("🇮🇱", "Израиль"),
    "ZA": ("🇿🇦", "ЮАР"), "MX": ("🇲🇽", "Мексика"), "AR": ("🇦🇷", "Аргентина"),
}


def get_flag(country_code: str) -> str:
    if not country_code:
        return "🌐"
    info = COUNTRY_MAP.get(country_code.upper())
    return info[0] if info else "🌐"


def get_country_name(country_code: str) -> str:
    if not country_code:
        return ""
    info = COUNTRY_MAP.get(country_code.upper())
    return info[1] if info else country_code


def lookup_ip_country(ip: str, callback: Callable[[Optional[str]], None]):
    """Async IP geolocation lookup"""
    def _lookup():
        try:
            # Try multiple APIs
            apis = [
                f"https://ipapi.co/{ip}/country/",
                f"https://ip-api.com/json/{ip}?fields=countryCode",
            ]
            for api_url in apis:
                try:
                    req = urllib.request.Request(
                        api_url,
                        headers={"User-Agent": "NexiaVPN/1.0"}
                    )
                    with urllib.request.urlopen(req, timeout=5) as resp:
                        content = resp.read().decode("utf-8").strip()
                        
                        # ipapi.co returns plain country code
                        if len(content) == 2 and content.isalpha():
                            callback(content.upper())
                            return
                        
                        # ip-api.com returns JSON
                        try:
                            data = json.loads(content)
                            code = data.get("countryCode", "")
                            if code:
                                callback(code.upper())
                                return
                        except json.JSONDecodeError:
                            pass
                except Exception:
                    continue
            
            callback(None)
        except Exception as e:
            logger.debug(f"GeoIP lookup failed for {ip}: {e}")
            callback(None)

    t = threading.Thread(target=_lookup, daemon=True)
    t.start()
