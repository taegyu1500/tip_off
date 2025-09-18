from __future__ import annotations
import json, socket, threading, time, uuid
from dataclasses import dataclass
from typing import Optional
from app.core.bus import EventBus
from .server_client import ServerClient, ServerConfig

@dataclass
class DmConfig:
    user_id: str
    room_id: str
    anon_nick: str
    listen_port: int   # UDP_DM_PORT
    recv_buf: int = 16384
    enable_server: bool = True  # 서버 연동 활성화
    server_host: str = "127.0.0.1"
    server_http_port: int = 8080
    server_udp_port: int = 5002

class DmService:
    """
    - 수신: 0.0.0.0:listen_port 바인드 후 DM 메시지 수신하여 EventBus로 전달
    - 송신: 상대 IP:상대 DM 포트로 JSON 유니캐스트 전송
    - 서버로도 메시지 전송하여 히스토리 저장
    """
    def __init__(self, cfg: DmConfig, bus: EventBus):
        self.cfg = cfg
        self.bus = bus
        self._stop = threading.Event()
        self._rx_th: Optional[threading.Thread] = None
        
        # 서버 클라이언트 초기화
        if cfg.enable_server:
            server_cfg = ServerConfig(
                host=cfg.server_host,
                http_port=cfg.server_http_port,
                udp_bridge_port=cfg.server_udp_port
            )
            self.server_client = ServerClient(server_cfg)
        else:
            self.server_client = None

    def start(self):
        self._stop.clear()
        self._rx_th = threading.Thread(target=self._rx_loop, name="dm-rx", daemon=True)
        self._rx_th.start()

    def stop(self):
        self._stop.set()
        if self._rx_th: self._rx_th.join(timeout=1.0)

    # --- 송신 ---
    def send_dm(self, to_ip: str, to_port: int, text: str, to_user_id: str = None):
        msg = {
            "type": "dm",
            "room_id": self.cfg.room_id,
            "from": self.cfg.user_id,
            "to": to_user_id,  # DM 대상 사용자 ID
            "nick": self.cfg.anon_nick,
            "text": text,
            "msg_id": str(uuid.uuid4()),
            "ts": time.time(),
        }
        try:
            # 직접 UDP 전송
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.sendto(json.dumps(msg, ensure_ascii=False).encode("utf-8"), (to_ip, to_port))
                
            # 서버로도 전송 (히스토리 저장용)
            if self.server_client:
                self.server_client.send_message_to_server(msg)
                
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
