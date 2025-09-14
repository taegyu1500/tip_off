from __future__ import annotations
import json, socket, threading, time, uuid
from dataclasses import dataclass
from typing import Optional
from app.core.bus import EventBus

@dataclass
class DmConfig:
    user_id: str
    room_id: str
    anon_nick: str
    listen_port: int   # UDP_DM_PORT
    recv_buf: int = 16384

class DmService:
    """
    - 수신: 0.0.0.0:listen_port 바인드 후 DM 메시지 수신하여 EventBus로 전달
    - 송신: 상대 IP:상대 DM 포트로 JSON 유니캐스트 전송
    """
    def __init__(self, cfg: DmConfig, bus: EventBus):
        self.cfg = cfg
        self.bus = bus
        self._stop = threading.Event()
        self._rx_th: Optional[threading.Thread] = None

    def start(self):
        self._stop.clear()
        self._rx_th = threading.Thread(target=self._rx_loop, name="dm-rx", daemon=True)
        self._rx_th.start()

    def stop(self):
        self._stop.set()
        if self._rx_th: self._rx_th.join(timeout=1.0)

    # --- 송신 ---
    def send_dm(self, to_ip: str, to_port: int, text: str):
        msg = {
            "type": "dm",
            "room_id": self.cfg.room_id,
            "from": self.cfg.user_id,
            "nick": self.cfg.anon_nick,
            "text": text,
            "msg_id": str(uuid.uuid4()),
            "ts": time.time(),
        }
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(json.dumps(msg, ensure_ascii=False).encode("utf-8"), (to_ip, to_port))
        except Exception as e:
            print("[dm] tx error:", e)

    # --- 수신 ---
    def _rx_loop(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind(("0.0.0.0", self.cfg.listen_port))
            s.settimeout(0.5)
            while not self._stop.is_set():
                try:
                    data, _ = s.recvfrom(self.cfg.recv_buf)
                except socket.timeout:
                    continue
                except Exception as e:
                    print("[dm] rx error:", e)
                    continue

                try:
                    msg = json.loads(data.decode("utf-8"))
                except Exception:
                    continue

                if not isinstance(msg, dict) or msg.get("type") != "dm":
                    continue
                if msg.get("room_id") != self.cfg.room_id:
                    continue
                if msg.get("from") == self.cfg.user_id:
                    continue

                self.bus.post("dm_chat",
                              from_uid=msg.get("from"),
                              nick=msg.get("nick"),
                              text=msg.get("text",""))
