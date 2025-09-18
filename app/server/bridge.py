"""
중앙 서버 가교 - 메시지 수집 및 DB 저장/조회 서비스
"""
import json
import socket
import threading
import time
from datetime import datetime
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

from app.db.database import DatabaseManager
from app.db.models import Message, MessageType, User, Room
from app.core.bus import EventBus

@dataclass
class ServerBridgeConfig:
    db_path: str = "tipoff.db"
    http_port: int = 8080
    udp_listen_port: int = 5002  # 새로운 포트로 메시지 수집
    host: str = "0.0.0.0"

class MessageCollectorService:
    """UDP로 전송되는 메시지를 수집하여 DB에 저장"""
    
    def __init__(self, config: ServerBridgeConfig, db_manager: DatabaseManager):
        self.config = config
        self.db = db_manager
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """서비스 시작"""
        self._stop.clear()
        self._thread = threading.Thread(target=self._udp_listen_loop, name="msg-collector", daemon=True)
        self._thread.start()
        print(f"[서버] 메시지 수집 서비스 시작 - UDP:{self.config.udp_listen_port}")

    def stop(self):
        """서비스 중지"""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _udp_listen_loop(self):
        """UDP 메시지 수신 루프"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((self.config.host, self.config.udp_listen_port))
            s.settimeout(0.5)
            
            while not self._stop.is_set():
                try:
                    data, addr = s.recvfrom(16384)
                    self._process_message(data, addr)
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"[서버] UDP 수신 오류: {e}")

    def _process_message(self, data: bytes, addr: tuple):
        """수신된 메시지 처리"""
        try:
            msg_data = json.loads(data.decode("utf-8"))
            self._save_message_to_db(msg_data, addr)
        except Exception as e:
            print(f"[서버] 메시지 처리 오류: {e}")

    def _save_message_to_db(self, msg_data: dict, addr: tuple):
        """메시지를 DB에 저장"""
        try:
            # 메시지 타입 결정
            msg_type = MessageType.LOBBY if msg_data.get("type") == "chat" else MessageType.DM
            
            message = Message(
                msg_id=msg_data.get("msg_id", ""),
                room_id=msg_data.get("room_id", "lobby"),
                message_type=msg_type,
                from_user_id=msg_data.get("from", ""),
                to_user_id=msg_data.get("to"),  # DM의 경우
                nick=msg_data.get("nick", ""),
                text=msg_data.get("text", ""),
                timestamp=datetime.fromtimestamp(msg_data.get("ts", time.time()))
            )
            
            # DB에 저장
            self.db.save_message(message)
            
            # 사용자 정보도 업데이트
            user = User(
                user_id=message.from_user_id,
                anon_nick=message.nick,
                last_seen=message.timestamp,
                ip=addr[0],
                room_id=message.room_id
            )
            self.db.save_user(user)
            
            print(f"[서버] 메시지 저장: {message.nick} -> {message.text[:50]}...")
            
        except Exception as e:
            print(f"[서버] DB 저장 오류: {e}")

class APIHandler(BaseHTTPRequestHandler):
    """HTTP API 핸들러"""
    
    def __init__(self, *args, **kwargs):
        # db_manager는 클래스 변수로 설정됨
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """GET 요청 처리"""
        try:
            parsed_path = urllib.parse.urlparse(self.path)
            path = parsed_path.path
            query = urllib.parse.parse_qs(parsed_path.query)
            
            if path == "/api/messages/lobby":
                self._handle_lobby_messages(query)
            elif path == "/api/messages/dm":
                self._handle_dm_messages(query)
            elif path == "/api/users":
                self._handle_users(query)
            elif path == "/api/stats":
                self._handle_stats()
            elif path == "/health":
                self._send_json_response({"status": "ok"})
            else:
                self._send_error(404, "Not Found")
                
        except Exception as e:
            print(f"[서버] API 오류: {e}")
            self._send_error(500, "Internal Server Error")

    def do_OPTIONS(self):
        """CORS preflight 요청 처리"""
        self._send_cors_headers()
        self.end_headers()

    def _handle_lobby_messages(self, query: Dict[str, List[str]]):
        """로비 메시지 조회"""
        room_id = query.get("room_id", ["lobby"])[0]
        limit = int(query.get("limit", ["50"])[0])
        
        messages = self.db.get_lobby_messages(room_id, limit)
        messages_data = [self._message_to_dict(msg) for msg in messages]
        self._send_json_response({"messages": messages_data})

    def _handle_dm_messages(self, query: Dict[str, List[str]]):
        """DM 메시지 조회"""
        user1 = query.get("user1", [""])[0]
        user2 = query.get("user2", [""])[0]
        limit = int(query.get("limit", ["50"])[0])
        
        if not user1 or not user2:
            self._send_error(400, "user1 and user2 parameters required")
            return
            
        messages = self.db.get_dm_messages(user1, user2, limit)
        messages_data = [self._message_to_dict(msg) for msg in messages]
        self._send_json_response({"messages": messages_data})

    def _handle_users(self, query: Dict[str, List[str]]):
        """사용자 목록 조회"""
        room_id = query.get("room_id", ["lobby"])[0]
        users = self.db.get_room_users(room_id)
        users_data = [self._user_to_dict(user) for user in users]
        self._send_json_response({"users": users_data})

    def _handle_stats(self):
        """통계 조회"""
        stats = self.db.get_stats()
        self._send_json_response(stats)

    def _message_to_dict(self, message: Message) -> dict:
        """Message 객체를 딕셔너리로 변환"""
        return {
            "id": message.id,
            "msg_id": message.msg_id,
            "room_id": message.room_id,
            "type": message.message_type.value,
            "from": message.from_user_id,
            "to": message.to_user_id,
            "nick": message.nick,
            "text": message.text,
            "timestamp": message.timestamp.isoformat(),
            "created_at": message.created_at.isoformat()
        }

    def _user_to_dict(self, user: User) -> dict:
        """User 객체를 딕셔너리로 변환"""
        return {
            "user_id": user.user_id,
            "anon_nick": user.anon_nick,
            "last_seen": user.last_seen.isoformat(),
            "ip": user.ip,
            "dm_port": user.dm_port,
            "room_id": user.room_id
        }

    def _send_json_response(self, data: dict, status: int = 200):
        """JSON 응답 전송"""
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _send_cors_headers(self):
        """CORS 헤더 전송"""
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_error(self, status: int, message: str):
        """에러 응답 전송"""
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        error_data = {"error": message, "status": status}
        self.wfile.write(json.dumps(error_data).encode("utf-8"))

    def log_message(self, format, *args):
        """로그 메시지 오버라이드 (너무 많은 로그 방지)"""
        pass

class HTTPAPIService:
    """HTTP API 서비스"""
    
    def __init__(self, config: ServerBridgeConfig, db_manager: DatabaseManager):
        self.config = config
        self.db = db_manager
        self.server: Optional[HTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """서비스 시작"""
        # 핸들러 클래스에 db_manager 연결
        APIHandler.db = self.db
        
        self.server = HTTPServer((self.config.host, self.config.http_port), APIHandler)
        self._thread = threading.Thread(target=self.server.serve_forever, name="http-api", daemon=True)
        self._thread.start()
        print(f"[서버] HTTP API 서비스 시작 - http://{self.config.host}:{self.config.http_port}")

    def stop(self):
        """서비스 중지"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()
        if self._thread:
            self._thread.join(timeout=1.0)

class ServerBridge:
    """중앙 서버 가교 - 메시지 수집 및 API 제공"""
    
    def __init__(self, config: ServerBridgeConfig):
        self.config = config
        self.db = DatabaseManager(config.db_path)
        self.collector = MessageCollectorService(config, self.db)
        self.api_service = HTTPAPIService(config, self.db)

    def start(self):
        """서버 시작"""
        print("[서버] TipOff 서버 브리지 시작")
        
        # 기본 룸 생성
        default_room = Room(room_id="lobby", name="로비")
        self.db.save_room(default_room)
        
        # 서비스 시작
        self.collector.start()
        self.api_service.start()
        
        print(f"[서버] 메시지 수집: UDP {self.config.udp_listen_port}")
        print(f"[서버] API 서비스: HTTP {self.config.http_port}")

    def stop(self):
        """서버 중지"""
        print("[서버] 서버 중지 중...")
        self.collector.stop()
        self.api_service.stop()
        print("[서버] 서버 중지 완료")

    def cleanup_old_data(self, days: int = 30):
        """오래된 데이터 정리"""
        self.db.cleanup_old_data(days)
        print(f"[서버] {days}일 이상 된 데이터 정리 완료")

    def get_stats(self) -> dict:
        """서버 통계 조회"""
        return self.db.get_stats()

def main():
    """서버 단독 실행용"""
    config = ServerBridgeConfig()
    server = ServerBridge(config)
    
    try:
        server.start()
        print("[서버] 서버가 실행 중입니다. Ctrl+C로 종료하세요.")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()

if __name__ == "__main__":
    main()