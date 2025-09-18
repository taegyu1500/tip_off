"""
메시지 히스토리 관리
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.net.server_client import ServerClient, ServerConfig

class HistoryManager:
    """메시지 히스토리 관리자"""
    
    def __init__(self, server_client: Optional[ServerClient] = None):
        self.server_client = server_client

    def load_lobby_history(self, room_id: str = "lobby", limit: int = 50) -> List[Dict[str, Any]]:
        """로비 히스토리 로드"""
        if not self.server_client or not self.server_client.is_server_available():
            return []
            
        messages = self.server_client.get_lobby_messages(room_id, limit)
        return self._format_messages(messages)

    def load_dm_history(self, user1: str, user2: str, limit: int = 50) -> List[Dict[str, Any]]:
        """DM 히스토리 로드"""
        if not self.server_client or not self.server_client.is_server_available():
            return []
            
        messages = self.server_client.get_dm_messages(user1, user2, limit)
        return self._format_messages(messages)

    def _format_messages(self, messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """메시지 포맷팅"""
        formatted = []
        for msg in messages:
            formatted.append({
                "text": msg.get("text", ""),
                "nick": msg.get("nick", ""),
                "from_uid": msg.get("from", ""),
                "to_uid": msg.get("to"),
                "timestamp": msg.get("timestamp", ""),
                "type": msg.get("type", "lobby"),
                "is_history": True  # 히스토리 메시지임을 표시
            })
        return formatted

    def get_server_stats(self) -> Dict[str, Any]:
        """서버 통계 조회"""
        if not self.server_client or not self.server_client.is_server_available():
            return {}
        return self.server_client.get_stats()