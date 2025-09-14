from __future__ import annotations
import json, socket, threading, time
from dataclasses import dataclass
from typing import Optional
from app.core.bus import EventBus

@dataclass
class PresenceConfig:
    user_id: str
    room_id: str
    anon_nick: str
    broadcast_ip: str
    port: int            # UDP_PORT
    dm_port: int         # UDP_DM_PORT
    interval_sec: float = 2.0
    recv_buf: int = 8192

class PresenceService:
    def __init__(self, cfg: PresenceConfig, bus: EventBus):
        self.cfg = cfg
        self.bus = bus
        self._stop = threading.Event()
        self._tx_th: Optional[threading.Thread] = None
        self._rx_th: Optional[threading.Thread] = None

    def start(self):
        self._stop.clear()
        self._tx_th = threading.Thread(target=self._tx_loop, name="presence-tx", daemon=True)
        self._rx_th = threading.Thread(target=self._rx_loop, name="presence-rx", daemon=True)
        self._tx_th.start()
        self._rx_th.start()

    def stop(self):
        self._stop.set()
        if self._tx_th: self._tx_th.join(timeout=1.0)
        if self._rx_th: self._rx_th.join(timeout=1.0)

    def _tx_loop(self):
        payload = {
            "type": "hello",
            "room_id": self.cfg.room_id,
            "user_id": self.cfg.user_id,
            "nick": self.cfg.anon_nick,
            "dm": self.cfg.dm_port,   # ← DM 포트 공지
        }
        addr = (self.cfg.broadcast_ip, self.cfg.port)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    s.sendto(json.dumps(payload).encode("utf-8"), addr)
                except Exception as e:
                    print("[presence] tx error:", e)
                self._stop.wait(self.cfg.interval_sec)

    def _rx_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.cfg.port))
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    data, peer = s.recvfrom(self.cfg.recv_buf)
                except socket.timeout:
                    continue
                except Exception as e:
                    print("[presence] rx error:", e)
                    continue

                try:
                    msg = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(msg, dict): 
                    continue
                if msg.get("type") != "hello":
                    continue
                if msg.get("room_id") != self.cfg.room_id:
                    continue
                from_uid = msg.get("user_id")
                if not from_uid or from_uid == self.cfg.user_id:
                    continue

                # peer IP는 소켓에서 받은 주소로 신뢰
                peer_ip = peer[0]
                peer_dm = msg.get("dm")

                self.bus.post("presence_seen",
                              user_id=from_uid,
                              anon_nick=msg.get("nick"),
                              ip=peer_ip,
                              dm_port=peer_dm)
