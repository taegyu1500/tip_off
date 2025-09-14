import argparse

def _str2bool(v: str | bool):
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ("1","true","yes","on","y","t"): return True
    if s in ("0","false","no","off","n","f"): return False
    raise argparse.ArgumentTypeError(f"boolean value expected, got '{v}'")

def parse_cli_args(argv: list[str] | None = None) -> dict:
    """
    argparse로 CLI 플래그를 파싱해서 AppConfig 키로 매핑된 dict를 반환.
    값이 주어지지 않은 항목은 dict에 포함하지 않음(None 제외).
    """
    p = argparse.ArgumentParser(prog="tipoff", add_help=True)

    # 기본/네트워크
    p.add_argument("--user-id", dest="USER_ID")
    p.add_argument("--room", dest="ROOM_ID")
    p.add_argument("--mode", choices=["lan","proxy"], dest="MODE")
    p.add_argument("--zmq-host", dest="ZMQ_HOST")
    p.add_argument("--zmq-port", type=int, dest="ZMQ_PORT")

    p.add_argument("--udp-port", type=int, dest="UDP_PORT")
    p.add_argument("--udp-chat-port", type=int, dest="UDP_CHAT_PORT")
    p.add_argument("--udp-dm-port", type=int, dest="UDP_DM_PORT")
    p.add_argument("--broadcast-ip", dest="BROADCAST_IP")
    p.add_argument("--tz", dest="TZ")

    # 알림/창
    p.add_argument("--topmost-default", type=_str2bool, dest="TOPMOST_DEFAULT")
    p.add_argument("--topmost-on-notify", type=_str2bool, dest="TOPMOST_ON_NOTIFY")
    p.add_argument("--topmost-on-notify-ms", type=int, dest="TOPMOST_ON_NOTIFY_MS")
    p.add_argument("--auto-open-dm", type=_str2bool, dest="AUTO_OPEN_DM")
    p.add_argument("--auto-focus-on-dm", choices=["true","false","mention"], dest="AUTO_FOCUS_ON_DM")
    p.add_argument("--sound-on-dm", type=_str2bool, dest="SOUND_ON_DM")

    # 기타
    p.add_argument("--log-level", choices=["INFO","DEBUG","WARN","ERROR"], dest="LOG_LEVEL")

    ns = p.parse_args(argv)  # argv=None이면 sys.argv[1:] 사용
    # None이 아닌 항목만 dict로
    out = {k: v for k, v in vars(ns).items() if v is not None}
    return out

def cli_layer(argv: list[str] | None = None) -> dict:
    """
    load_effective_config()에서 불러 쓰는 레이어.
    """
    return parse_cli_args(argv)
