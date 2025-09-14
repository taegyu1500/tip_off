"""
LobbyService
- 로비 채팅 메시지를 UDP 브로드캐스트로 송신
- 동일 포트에서 수신하여 같은 room_id의 타인 메시지를 EventBus로 전달
"""
from __future__ import annotations
import json, socket, threading, time, uuid
from dataclasses import dataclass
from typing import Optional
from app.core.bus import EventBus

@dataclass
class LobbyConfig:
    user_id: str
    room_id: str
    anon_nick: str
    broadcast_ip: str
    port: int  # UDP_CHAT_PORT
    recv_buf: int = 16384

class LobbyService:
    def __init__(self, cfg: LobbyConfig, bus: EventBus):
        self.cfg = cfg
        self.bus = bus
        self._stop = threading.Event()
        self._rx_th: Optional[threading.Thread] = None

    def start(self):
        self._stop.clear()
        self._rx_th = threading.Thread(target=self._rx_loop, name="lobby-rx", daemon=True)
        self._rx_th.start()

    def stop(self):
        self._stop.set()
        if self._rx_th: self._rx_th.join(timeout=1.0)

    # ---- 송신 ----
    def send_lobby(self, text: str):
        msg = {
            "type": "chat",
            "room_id": self.cfg.room_id,
            "from": self.cfg.user_id,
            "nick": self.cfg.anon_nick,
            "text": text,
            "msg_id": str(uuid.uuid4()),
            "ts": time.time(),
        }
        addr = (self.cfg.broadcast_ip, self.cfg.port)
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
                s.sendto(json.dumps(msg, ensure_ascii=False).encode("utf-8"), addr)
        except Exception as e:
            print("[lobby] tx error:", e)

    # ---- 수신 ----
    def _rx_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.cfg.port))
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    data, _ = s.recvfrom(self.cfg.recv_buf)
                except socket.timeout:
                    continue
                except Exception as e:
                    print("[lobby] rx error:", e)
                    continue

                try:
                    msg = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(msg, dict) or msg.get("type") != "chat":
                    continue
                if msg.get("room_id") != self.cfg.room_id:
                    continue
                if msg.get("from") == self.cfg.user_id:
                    # 내가 보낸 브로드캐스트는 표시하지 않음(이미 로컬에 찍었음)
                    continue

                self.bus.post("lobby_chat",
                              from_uid=msg.get("from"),
                              nick=msg.get("nick"),
                              text=msg.get("text", ""))
