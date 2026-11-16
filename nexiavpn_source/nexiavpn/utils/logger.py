"""
Safe Logger - never logs VPN links or passwords
"""
import logging
import os
import re
from datetime import datetime


class SafeFilter(logging.Filter):
    """Filter out sensitive data from logs"""
    
    SENSITIVE_PATTERNS = [
        r'vless://[^\s]+',
        r'vmess://[^\s]+',
        r'trojan://[^\s]+',
        r'ss://[^\s]+',
        r'password["\s:=]+[^\s,}]+',
        r'uuid["\s:=]+[0-9a-f-]{36}',
    ]
    
    def filter(self, record):
        msg = str(record.getMessage())
        for pattern in self.SENSITIVE_PATTERNS:
            msg = re.sub(pattern, '[REDACTED]', msg, flags=re.IGNORECASE)
        record.msg = msg
        record.args = ()
        return True


class Logger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._setup()
        return cls._instance
    
    def _setup(self):
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        self._logger = logging.getLogger("NexiaVPN")
        self._logger.setLevel(logging.DEBUG)
        
        # Safe filter
        safe_filter = SafeFilter()
        
        # File handler
        log_file = os.path.join(log_dir, f"nexiavpn_{datetime.now().strftime('%Y%m%d')}.log")
        fh = logging.FileHandler(log_file, encoding='utf-8')
        fh.setLevel(logging.DEBUG)
        fh.addFilter(safe_filter)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.addFilter(safe_filter)
        
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s: %(message)s',
            datefmt='%H:%M:%S'
        )
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        self._logger.addHandler(fh)
        self._logger.addHandler(ch)
    
    def info(self, msg): self._logger.info(msg)
    def debug(self, msg): self._logger.debug(msg)
    def warning(self, msg): self._logger.warning(msg)
    def error(self, msg): self._logger.error(msg)
    def critical(self, msg): self._logger.critical(msg)


# Global instance
_logger = Logger()

def get_logger():
    return _logger
