from pydantic import BaseModel, field_validator
from typing import Literal
import re, ipaddress

class AppConfig(BaseModel):
    CONFIG_VERSION: int = 1

    USER_ID: str = ""
    ROOM_ID: str = "lobby"

    MODE: Literal["lan", "proxy"] = "lan"
    ZMQ_HOST: str = "127.0.0.1"
    ZMQ_PORT: int = 5555

    UDP_PORT: int = 5000
    UDP_CHAT_PORT: int = 5001
    UDP_DM_PORT: int = 5002

    BROADCAST_IP: str = "192.168.100.255"
    TZ: str = "Asia/Seoul"

    TOPMOST_DEFAULT: bool = False
    TOPMOST_ON_NOTIFY: bool = True
    TOPMOST_ON_NOTIFY_MS: int = 3000
    AUTO_OPEN_DM: bool = True
    AUTO_FOCUS_ON_DM: Literal["true", "false", "mention"] | str = "mention"
    SOUND_ON_DM: bool = True

    SEQ_GAP_WAIT_MS: int = 300
    LOG_LEVEL: Literal["INFO", "DEBUG", "WARN", "ERROR"] = "INFO"

    @field_validator("USER_ID")
    @classmethod
    def validate_user_id(cls, v: str):
        v = v or ""
        if v == "":
            return v
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", v):
            raise ValueError("USER_ID는 [A-Za-z0-9_-], 1–32자만 허용")
        return v

    @field_validator("ROOM_ID")
    @classmethod
    def validate_room_id(cls, v: str):
        if not (1 <= len(v) <= 64):
            raise ValueError("ROOM_ID는 1–64자")
        if " " in v:
            raise ValueError("ROOM_ID에는 공백 불가")
        return v

    @field_validator("ZMQ_PORT", "UDP_PORT", "UDP_CHAT_PORT", "UDP_DM_PORT")
    @classmethod
    def validate_ports(cls, v: int):
        if not (1024 <= v <= 65535):
            raise ValueError("포트는 1024–65535")
        return v

    @field_validator("BROADCAST_IP")
    @classmethod
    def validate_ip(cls, v: str):
        ipaddress.IPv4Address(v)
        return v

    @field_validator("AUTO_FOCUS_ON_DM")
    @classmethod
    def normalize_focus(cls, v):
        if v in (True, False):
            return "true" if v else "false"
        if v not in ("true", "false", "mention"):
            raise ValueError("AUTO_FOCUS_ON_DM은 true|false|mention")
        return v
