"""
데이터 모델 정의
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List
from enum import Enum

class MessageType(Enum):
    LOBBY = "lobby"
    DM = "dm"

@dataclass
class Message:
    id: Optional[int] = None
    msg_id: str = ""  # UUID
    room_id: str = ""
    message_type: MessageType = MessageType.LOBBY
    from_user_id: str = ""
    to_user_id: Optional[str] = None  # DM의 경우만
    nick: str = ""
    text: str = ""
    timestamp: datetime = None
    created_at: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
        if self.created_at is None:
            self.created_at = datetime.now()

@dataclass
class User:
    user_id: str
    anon_nick: str
    last_seen: datetime
    ip: Optional[str] = None
    dm_port: Optional[int] = None
    room_id: str = "lobby"

@dataclass
class Room:
    room_id: str
    name: str
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()