import os

# 타입 힌트/변환용 테이블
INT_KEYS = {
    "CONFIG_VERSION",
    "ZMQ_PORT", "UDP_PORT", "UDP_CHAT_PORT", "UDP_DM_PORT",
    "TOPMOST_ON_NOTIFY_MS", "SEQ_GAP_WAIT_MS",
}
BOOL_KEYS = {
    "TOPMOST_DEFAULT", "TOPMOST_ON_NOTIFY",
    "AUTO_OPEN_DM", "SOUND_ON_DM",
}
# 문자열이지만 제한된 선택지가 있는 키는 스키마에서 최종 검증

def _to_bool(s: str) -> bool:
    return str(s).strip().lower() in ("1","true","yes","on","y","t")

def env_layer() -> dict:
    """
    환경변수로 덮어쓰는 레이어.
    - 키 이름은 AppConfig 키와 동일하게 대문자 사용 (예: USER_ID, BROADCAST_IP)
    - 값 타입은 INT_KEYS/BOOL_KEYS에 맞춰 변환
    """
    out: dict = {}
    # 화이트리스트: 스키마 키만 허용
    keys = {
        "CONFIG_VERSION",
        "USER_ID","ROOM_ID","MODE","ZMQ_HOST","ZMQ_PORT",
        "UDP_PORT","UDP_CHAT_PORT","UDP_DM_PORT",
        "BROADCAST_IP","TZ",
        "TOPMOST_DEFAULT","TOPMOST_ON_NOTIFY","TOPMOST_ON_NOTIFY_MS",
        "AUTO_OPEN_DM","AUTO_FOCUS_ON_DM","SOUND_ON_DM",
        "SEQ_GAP_WAIT_MS","LOG_LEVEL",
    }
    for k in keys:
        if k in os.environ:
            raw = os.environ[k]
            if k in INT_KEYS:
                try: out[k] = int(raw)
                except ValueError: pass
            elif k in BOOL_KEYS:
                out[k] = _to_bool(raw)
            else:
                # AUTO_FOCUS_ON_DM 등은 문자열 그대로 (스키마에서 검증)
                out[k] = raw
    return out

def merge_layers(*layers: dict) -> dict:
    """
    왼쪽부터 오른쪽으로 순차 병합, 오른쪽이 우선.
    예) merge_layers(file, env, cli) → CLI가 최종 승자
    """
    result: dict = {}
    for layer in layers:
        if not layer: continue
        result.update(layer)
    return result
