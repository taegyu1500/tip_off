import tkinter as tk
from datetime import datetime, timedelta

from app.config import load_effective_config
from app.core.state import AppState
from app.core.bus import EventBus
from app.ui.main_window import MainWindow
from app.net.presence import PresenceService, PresenceConfig
from app.net.lobby import LobbyService, LobbyConfig
from app.net.dm import DmService, DmConfig
from app.notify.attention import AttentionManager

PRUNE_SECONDS = 15
PUMP_PRUNE_MS = 3000

def main():
    cfg = load_effective_config()

    root = tk.Tk()
    bus = EventBus(root)
    attention = AttentionManager(
        root,
        topmost_default=bool(cfg.TOPMOST_DEFAULT),
        bump_ms=int(cfg.TOPMOST_ON_NOTIFY_MS),
        topmost_on_notify=bool(cfg.TOPMOST_ON_NOTIFY),
    )

    state = AppState(
        user_id=(cfg.USER_ID or "anon"),
        room_id=(cfg.ROOM_ID or "lobby"),
    )

    # 네트워크 서비스 핸들 잡아두기
    services = {"lobby": None, "dm": None}

    def _send_lobby(text: str):
        if services["lobby"]:
            services["lobby"].send_lobby(text)

    def _send_dm(target_uid: str, text: str):
        ent = state.roster.get(target_uid)
        if not ent or not ent.ip or not ent.dm_port:
            print(f"[dm] route missing for @{target_uid} (ip/port 없음)")
            return
        services["dm"].send_dm(ent.ip, ent.dm_port, text)

    # UI
    ui = MainWindow(root, state, send_lobby_cb=_send_lobby, send_dm_cb=_send_dm)

    # --- 이벤트 버스 핸들러 ---
    def on_presence_seen(ev: dict):
        state.upsert_peer(
            ev["user_id"],
            anon_nick=ev.get("anon_nick"),
            ip=ev.get("ip"),
            dm_port=ev.get("dm_port"),
        )
        ui.refresh_roster()
    bus.on("presence_seen", on_presence_seen)

    def on_lobby_chat(ev: dict):
        # 로비 수신: 메시지 표시만, 최상단 팝업은 하지 않음
        ui.add_message(ev.get("text", ""), mine=False, target=None, meta_nick=ev.get("nick"))
    bus.on("lobby_chat", on_lobby_chat)

    def on_dm_chat(ev: dict):
        from_uid = ev.get("from_uid")
        state.ensure_dm_session(from_uid)
        ui._ensure_tab(from_uid)
        ui.add_message(ev.get("text", ""), mine=False, target=from_uid, from_uid=from_uid)
        # DM 수신: 창을 잠깐 최상단으로
        attention.bump()
    bus.on("dm_chat", on_dm_chat)

    # --- 서비스 시작 ---
    presence = PresenceService(PresenceConfig(
        user_id=state.user_id, room_id=state.room_id, anon_nick=state.anon_nick,
        broadcast_ip=cfg.BROADCAST_IP, port=cfg.UDP_PORT, dm_port=cfg.UDP_DM_PORT
    ), bus)
    presence.start()

    lobby = LobbyService(LobbyConfig(
        user_id=state.user_id, room_id=state.room_id, anon_nick=state.anon_nick,
        broadcast_ip=cfg.BROADCAST_IP, port=cfg.UDP_CHAT_PORT
    ), bus)
    lobby.start()
    services["lobby"] = lobby

    dm = DmService(DmConfig(
        user_id=state.user_id, room_id=state.room_id, anon_nick=state.anon_nick,
        listen_port=cfg.UDP_DM_PORT
    ), bus)
    dm.start()
    services["dm"] = dm

    # 버스 폴링 + 로스터 타임아웃 정리
    bus.start()

    def prune_roster():
        now = datetime.now()
        removed = False
        for uid, ent in list(state.roster.items()):
            if ent.is_self:
                continue
            if (now - ent.last_seen).total_seconds() > PRUNE_SECONDS:
                state.remove_peer(uid)
                removed = True
        if removed:
            ui.refresh_roster()
        root.after(PUMP_PRUNE_MS, prune_roster)

    root.after(PUMP_PRUNE_MS, prune_roster)

    def on_close():
        try:
            presence.stop()
            lobby.stop()
            dm.stop()
            bus.stop()
        finally:
            root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
