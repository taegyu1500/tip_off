# TipOff - 채팅 애플리케이션 (DB 서버 연동 버전)

## 개요

TipOff는 UDP 기반의 P2P 채팅 시스템에 중앙 서버를 추가하여 메시지 지속성을 제공하는 애플리케이션입니다.

## 주요 기능

- **로비 채팅**: UDP 브로드캐스트 기반 그룹 채팅
- **1:1 DM**: 직접 IP 연결을 통한 개인 메시지
- **메시지 히스토리**: 서버를 통한 메시지 저장 및 복원
- **사용자 관리**: 실시간 사용자 목록 및 상태 관리

## 아키텍처

### 기존 P2P 기능 (유지)
- UDP 브로드캐스트로 로비 메시지 전송
- UDP 유니캐스트로 DM 전송
- 실시간 presence 관리

### 새로 추가된 서버 기능
- **중앙 서버**: 모든 메시지 수집 및 DB 저장
- **SQLite DB**: 메시지, 사용자, 룸 정보 저장
- **HTTP API**: 메시지 히스토리 조회
- **자동 복원**: 클라이언트 시작 시 히스토리 로드

## 설치 및 실행

### 1. 의존성 설치

```bash
# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt
```

### 2. 서버 실행

```bash
# 터미널 1에서 서버 실행
source venv/bin/activate
python run_server.py
```

서버가 시작되면 다음과 같은 정보가 표시됩니다:
- DB 파일: `tipoff.db`
- HTTP API: `http://localhost:8080`
- UDP 수집: `localhost:5002`

### 3. 클라이언트 실행

```bash
# 터미널 2에서 클라이언트 실행
source venv/bin/activate
python -m app.main
```

## 네트워크 포트

| 서비스 | 포트 | 프로토콜 | 용도 |
|--------|------|----------|------|
| 서버 HTTP API | 8080 | TCP | 메시지 히스토리 조회 |
| 서버 메시지 수집 | 5002 | UDP | 클라이언트로부터 메시지 수집 |
| 로비 채팅 | 5001 | UDP | P2P 브로드캐스트 채팅 |
| DM | 5003 | UDP | P2P 직접 메시지 |
| Presence | 5000 | UDP | 사용자 상태 브로드캐스트 |

## 설정

`app/config/defaults.py`에서 다음 설정을 변경할 수 있습니다:

```python
# 서버 관련 설정
"SERVER_ENABLED": True,           # 서버 연동 활성화
"SERVER_HOST": "127.0.0.1",      # 서버 주소
"SERVER_HTTP_PORT": 8080,        # HTTP API 포트
"SERVER_UDP_PORT": 5002,         # UDP 수집 포트
"LOAD_HISTORY_ON_START": True,   # 시작 시 히스토리 로드
"HISTORY_LIMIT": 50,             # 로드할 히스토리 개수
```

## API 엔드포인트

### 서버 상태 확인
```bash
curl http://localhost:8080/health
```

### 로비 메시지 조회
```bash
curl "http://localhost:8080/api/messages/lobby?room_id=lobby&limit=50"
```

### DM 메시지 조회
```bash
curl "http://localhost:8080/api/messages/dm?user1=alice&user2=bob&limit=50"
```

### 사용자 목록 조회
```bash
curl "http://localhost:8080/api/users?room_id=lobby"
```

### 서버 통계 조회
```bash
curl http://localhost:8080/api/stats
```

## 데이터베이스

SQLite 데이터베이스(`tipoff.db`)에는 다음 테이블이 생성됩니다:

- **messages**: 모든 메시지 (로비 + DM)
- **users**: 사용자 정보 및 마지막 접속 시간
- **rooms**: 룸 정보

## 트러블슈팅

### 서버 연결 실패
1. 서버가 실행 중인지 확인: `ps aux | grep run_server`
2. 포트가 사용 중인지 확인: `netstat -tlnp | grep 8080`
3. 방화벽 설정 확인

### 메시지 히스토리 로드 안됨
1. 서버 로그 확인
2. `SERVER_ENABLED=True` 설정 확인
3. 네트워크 연결 상태 확인

### UDP 통신 문제
1. 브로드캐스트 주소 확인 (`BROADCAST_IP` 설정)
2. 포트 충돌 확인
3. 방화벽 UDP 포트 허용 확인

## 개발자 정보

### 프로젝트 구조
```
app/
├── db/          # 데이터베이스 모듈
├── server/      # 서버 브리지 모듈
├── net/         # 네트워크 서비스
├── core/        # 코어 로직 (상태, 히스토리)
├── ui/          # UI 컴포넌트
├── config/      # 설정 관리
└── notify/      # 알림 시스템
```

### 확장 가능성
- 다중 룸 지원
- 파일 전송 기능
- 암호화 통신
- 웹 클라이언트 인터페이스
- 사용자 인증 시스템