from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from datetime import datetime
import random

_ANON_NAMES = [
    "alice","bob","carol","dave","erin","frank","grace","heidi","ivan","judy",
    "karl","laura","mallory","nick","olivia","peggy","quentin","rupert","sybil","trent",
    "ursula","victor","wendy","xavier","yvonne","zack","amber","bruce","claire","dan",
    "ella","felix","george","hannah","isaac","jane","kevin","lily","mike","nina",
    "oscar","paula","queen","riley","simon","tina","uma","val","will","xena",
    "yuri","zoe"
]

def generate_anon_nick() -> str:
    return random.choice(_ANON_NAMES)

@dataclass
class RosterEntry:
    user_id: str
    anon_nick: Optional[str] = None
    is_self: bool = False
    last_seen: datetime = field(default_factory=datetime.now)
    ip: Optional[str] = None           # ← 추가: 피어의 최근 IP
    dm_port: Optional[int] = None      # ← 추가: 피어의 DM 수신 포트

@dataclass
class AppState:
    user_id: str
    room_id: str

    anon_nick: str = field(default_factory=generate_anon_nick)

    roster: Dict[str, RosterEntry] = field(default_factory=dict)
    dm_sessions: Set[str] = field(default_factory=set)
    messages: List[str] = field(default_factory=list)

    # ---- 로스터 ----
    def upsert_self(self):
        self.roster[self.user_id] = RosterEntry(
            user_id=self.user_id, anon_nick=self.anon_nick, is_self=True
        )

    def upsert_peer(self, user_id: str, anon_nick: Optional[str] = None,
                    ip: Optional[str] = None, dm_port: Optional[int] = None):
        ent = self.roster.get(user_id)
        if ent:
            ent.last_seen = datetime.now()
            if anon_nick: ent.anon_nick = anon_nick
            if ip: ent.ip = ip
            if dm_port: ent.dm_port = dm_port
        else:
            self.roster[user_id] = RosterEntry(
                user_id=user_id, anon_nick=anon_nick, is_self=False,
                ip=ip, dm_port=dm_port
            )

    def remove_peer(self, user_id: str):
        if user_id in self.roster and not self.roster[user_id].is_self:
            self.roster.pop(user_id, None)

    def list_roster(self) -> List[RosterEntry]:
        entries = list(self.roster.values())
        entries.sort(key=lambda e: (0 if e.is_self else 1, e.user_id.lower()))
        return entries

    # ---- DM 세션 ----
    def ensure_dm_session(self, user_id: str):
        if user_id != self.user_id:
            self.dm_sessions.add(user_id)

    def close_dm_session(self, user_id: str):
        self.dm_sessions.discard(user_id)
