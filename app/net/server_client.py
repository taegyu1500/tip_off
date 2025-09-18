"""
서버 연동 클라이언트 - 메시지 히스토리 조회
"""
import json
import requests
import socket
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass

@dataclass
class ServerConfig:
    host: str = "127.0.0.1"
    http_port: int = 8080
    udp_bridge_port: int = 5002
    timeout: int = 5

class ServerClient:
    """서버 API 클라이언트"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.base_url = f"http://{config.host}:{config.http_port}"
        self.session = requests.Session()
        self.session.timeout = config.timeout

    def send_message_to_server(self, msg_data: dict):
        """메시지를 서버로 전송 (UDP)"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                message = json.dumps(msg_data, ensure_ascii=False).encode("utf-8")
                s.sendto(message, (self.config.host, self.config.udp_bridge_port))
        except Exception as e:
            print(f"[클라이언트] 서버 전송 오류: {e}")

    def get_lobby_messages(self, room_id: str = "lobby", limit: int = 50) -> List[Dict[str, Any]]:
        """로비 메시지 히스토리 조회"""
        try:
            response = self.session.get(f"{self.base_url}/api/messages/lobby", 
                                      params={"room_id": room_id, "limit": limit})
            response.raise_for_status()
            return response.json().get("messages", [])
        except Exception as e:
            print(f"[클라이언트] 로비 메시지 조회 오류: {e}")
            return []

    def get_dm_messages(self, user1: str, user2: str, limit: int = 50) -> List[Dict[str, Any]]:
        """DM 메시지 히스토리 조회"""
        try:
            response = self.session.get(f"{self.base_url}/api/messages/dm",
                                      params={"user1": user1, "user2": user2, "limit": limit})
            response.raise_for_status()
            return response.json().get("messages", [])
        except Exception as e:
            print(f"[클라이언트] DM 메시지 조회 오류: {e}")
            return []

    def get_users(self, room_id: str = "lobby") -> List[Dict[str, Any]]:
        """사용자 목록 조회"""
        try:
            response = self.session.get(f"{self.base_url}/api/users",
                                      params={"room_id": room_id})
            response.raise_for_status()
            return response.json().get("users", [])
        except Exception as e:
            print(f"[클라이언트] 사용자 목록 조회 오류: {e}")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """서버 통계 조회"""
        try:
            response = self.session.get(f"{self.base_url}/api/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[클라이언트] 통계 조회 오류: {e}")
            return {}

    def is_server_available(self) -> bool:
        """서버 연결 상태 확인"""
        try:
            response = self.session.get(f"{self.base_url}/health")
            return response.status_code == 200
        except Exception:
            return False