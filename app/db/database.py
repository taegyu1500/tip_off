"""
SQLite 데이터베이스 관리
"""
import sqlite3
import os
from datetime import datetime
from typing import List, Optional, Tuple
from contextlib import contextmanager
from .models import Message, MessageType, User, Room

class DatabaseManager:
    def __init__(self, db_path: str = "tipoff.db"):
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        with self._get_connection() as conn:
            # 메시지 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    msg_id TEXT UNIQUE NOT NULL,
                    room_id TEXT NOT NULL,
                    message_type TEXT NOT NULL,
                    from_user_id TEXT NOT NULL,
                    to_user_id TEXT,
                    nick TEXT NOT NULL,
                    text TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            
            # 인덱스 생성
            conn.execute("CREATE INDEX IF NOT EXISTS idx_room_timestamp ON messages (room_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_dm_users ON messages (from_user_id, to_user_id, timestamp)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_msg_id ON messages (msg_id)")

            # 사용자 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    anon_nick TEXT NOT NULL,
                    last_seen REAL NOT NULL,
                    ip TEXT,
                    dm_port INTEGER,
                    room_id TEXT NOT NULL DEFAULT 'lobby'
                )
            """)

            # 룸 테이블
            conn.execute("""
                CREATE TABLE IF NOT EXISTS rooms (
                    room_id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)

            conn.commit()

    @contextmanager
    def _get_connection(self):
        """DB 연결 컨텍스트 매니저"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    # === 메시지 관련 ===
    def save_message(self, message: Message) -> int:
        """메시지 저장"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR IGNORE INTO messages 
                (msg_id, room_id, message_type, from_user_id, to_user_id, nick, text, timestamp, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message.msg_id,
                message.room_id,
                message.message_type.value,
                message.from_user_id,
                message.to_user_id,
                message.nick,
                message.text,
                message.timestamp.timestamp(),
                message.created_at.timestamp()
            ))
            conn.commit()
            return cursor.lastrowid

    def get_lobby_messages(self, room_id: str, limit: int = 100, before_timestamp: Optional[datetime] = None) -> List[Message]:
        """로비 메시지 조회"""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM messages 
                WHERE room_id = ? AND message_type = 'lobby'
            """
            params = [room_id]
            
            if before_timestamp:
                query += " AND timestamp < ?"
                params.append(before_timestamp.timestamp())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_message(row) for row in reversed(rows)]

    def get_dm_messages(self, user1: str, user2: str, limit: int = 100, before_timestamp: Optional[datetime] = None) -> List[Message]:
        """DM 메시지 조회"""
        with self._get_connection() as conn:
            query = """
                SELECT * FROM messages 
                WHERE message_type = 'dm' 
                AND ((from_user_id = ? AND to_user_id = ?) OR (from_user_id = ? AND to_user_id = ?))
            """
            params = [user1, user2, user2, user1]
            
            if before_timestamp:
                query += " AND timestamp < ?"
                params.append(before_timestamp.timestamp())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_message(row) for row in reversed(rows)]

    def get_recent_messages(self, room_id: str, limit: int = 50) -> List[Message]:
        """최근 메시지 조회 (로비 + DM)"""
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM messages 
                WHERE room_id = ? 
                ORDER BY timestamp DESC LIMIT ?
            """, (room_id, limit)).fetchall()
            return [self._row_to_message(row) for row in reversed(rows)]

    def _row_to_message(self, row) -> Message:
        """DB 행을 Message 객체로 변환"""
        return Message(
            id=row['id'],
            msg_id=row['msg_id'],
            room_id=row['room_id'],
            message_type=MessageType(row['message_type']),
            from_user_id=row['from_user_id'],
            to_user_id=row['to_user_id'],
            nick=row['nick'],
            text=row['text'],
            timestamp=datetime.fromtimestamp(row['timestamp']),
            created_at=datetime.fromtimestamp(row['created_at'])
        )

    # === 사용자 관련 ===
    def save_user(self, user: User):
        """사용자 정보 저장/업데이트"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO users 
                (user_id, anon_nick, last_seen, ip, dm_port, room_id)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user.user_id,
                user.anon_nick,
                user.last_seen.timestamp(),
                user.ip,
                user.dm_port,
                user.room_id
            ))
            conn.commit()

    def get_user(self, user_id: str) -> Optional[User]:
        """사용자 정보 조회"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM users WHERE user_id = ?
            """, (user_id,)).fetchone()
            
            if row:
                return User(
                    user_id=row['user_id'],
                    anon_nick=row['anon_nick'],
                    last_seen=datetime.fromtimestamp(row['last_seen']),
                    ip=row['ip'],
                    dm_port=row['dm_port'],
                    room_id=row['room_id']
                )
            return None

    def get_room_users(self, room_id: str, active_minutes: int = 15) -> List[User]:
        """룸의 활성 사용자 목록 조회"""
        cutoff = datetime.now().timestamp() - (active_minutes * 60)
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT * FROM users 
                WHERE room_id = ? AND last_seen > ?
                ORDER BY last_seen DESC
            """, (room_id, cutoff)).fetchall()
            
            return [User(
                user_id=row['user_id'],
                anon_nick=row['anon_nick'],
                last_seen=datetime.fromtimestamp(row['last_seen']),
                ip=row['ip'],
                dm_port=row['dm_port'],
                room_id=row['room_id']
            ) for row in rows]

    # === 룸 관련 ===
    def save_room(self, room: Room):
        """룸 정보 저장"""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO rooms (room_id, name, created_at)
                VALUES (?, ?, ?)
            """, (room.room_id, room.name, room.created_at.timestamp()))
            conn.commit()

    def get_room(self, room_id: str) -> Optional[Room]:
        """룸 정보 조회"""
        with self._get_connection() as conn:
            row = conn.execute("""
                SELECT * FROM rooms WHERE room_id = ?
            """, (room_id,)).fetchone()
            
            if row:
                return Room(
                    room_id=row['room_id'],
                    name=row['name'],
                    created_at=datetime.fromtimestamp(row['created_at'])
                )
            return None

    # === 유틸리티 ===
    def cleanup_old_data(self, days: int = 30):
        """오래된 데이터 정리"""
        cutoff = datetime.now().timestamp() - (days * 24 * 60 * 60)
        with self._get_connection() as conn:
            # 오래된 메시지 삭제
            conn.execute("DELETE FROM messages WHERE created_at < ?", (cutoff,))
            # 오래된 사용자 정보 삭제 (단, 최근 메시지가 있는 사용자는 제외)
            conn.execute("""
                DELETE FROM users 
                WHERE last_seen < ? 
                AND user_id NOT IN (
                    SELECT DISTINCT from_user_id FROM messages WHERE created_at > ?
                )
            """, (cutoff, cutoff))
            conn.commit()

    def get_stats(self) -> dict:
        """데이터베이스 통계 조회"""
        with self._get_connection() as conn:
            stats = {}
            stats['total_messages'] = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            stats['total_users'] = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            stats['total_rooms'] = conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]
            stats['lobby_messages'] = conn.execute("SELECT COUNT(*) FROM messages WHERE message_type = 'lobby'").fetchone()[0]
            stats['dm_messages'] = conn.execute("SELECT COUNT(*) FROM messages WHERE message_type = 'dm'").fetchone()[0]
            return stats