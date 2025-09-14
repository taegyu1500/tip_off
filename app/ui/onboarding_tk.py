import tkinter as tk
import re
from tkinter import ttk, messagebox
import random, string
from pydantic import ValidationError
from app.config.schema import AppConfig
from app.config.io import (
    atomic_write_yaml, config_paths, ensure_dir,
    FileLock, backup
)

FOCUS_LABEL2VALUE = {
    "DM만 허락": "mention",  # 멘션일 때만 포커스
    "전체 허락": "true",     # 모든 DM에 포커스
    "전체 거부": "false",    # 포커스 끔
}
FOCUS_VALUE2LABEL = {v: k for k, v in FOCUS_LABEL2VALUE.items()}


def _rand(n=6):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=n))

def run_onboarding_tk() -> AppConfig | None:
    root = tk.Tk()
    root.title("TIP-OFF 온보딩")
    root.geometry("420x380")

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)

    # USER_ID
    ttk.Label(frame, text="USER_ID (한글 미지원)").grid(row=0, column=0, sticky="w")
    e_user = ttk.Entry(frame, width=28); e_user.grid(row=0, column=1, sticky="ew")

    # ROOM_ID 입력칸 제거 → 자동 'lobby' 사용

    # MODE (기존 그대로 유지: lan/proxy 선택 UI는 남김)
    ttk.Label(frame, text="MODE (proxy 미지원)").grid(row=2, column=0, sticky="w")
    mode_var = tk.StringVar(value="lan")
    ttk.Radiobutton(frame, text="lan",   variable=mode_var, value="lan").grid(  row=2, column=1, sticky="w")
    ttk.Radiobutton(frame, text="proxy", variable=mode_var, value="proxy").grid(row=2, column=1, sticky="e")

    ttk.Label(frame, text="ZMQ_HOST (proxy)").grid(row=3, column=0, sticky="w")
    e_host = ttk.Entry(frame, width=28); e_host.insert(0, "127.0.0.1"); e_host.grid(row=3, column=1, sticky="ew")
    ttk.Label(frame, text="ZMQ_PORT (proxy)").grid(row=4, column=0, sticky="w")
    e_port = ttk.Entry(frame, width=28); e_port.insert(0, "5555"); e_port.grid(row=4, column=1, sticky="ew")

    top_on = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="새 메시지 오면 팝업", variable=top_on).grid(row=5, column=0, columnspan=2, sticky="w")

    auto_dm = tk.BooleanVar(value=True)
    ttk.Checkbutton(frame, text="DM 처음 오면 탭 자동 생성", variable=auto_dm).grid(row=6, column=0, columnspan=2, sticky="w")

    ttk.Label(frame, text="팝업 범위 설정").grid(row=7, column=0, sticky="w")
    focus_var = tk.StringVar(value=FOCUS_VALUE2LABEL["mention"])  # 기본 "mention"에 해당하는 라벨
    cb_focus = ttk.Combobox(
        frame,
        textvariable=focus_var,
        values=list(FOCUS_LABEL2VALUE.keys()),
        width=25,
        state="readonly"
    )
    cb_focus.grid(row=7, column=1, sticky="ew")

    def toggle_proxy(*_):
        enabled = (mode_var.get() == "proxy")
        e_host.config(state=("normal" if enabled else "disabled"))
        e_port.config(state=("normal" if enabled else "disabled"))
    mode_var.trace_add("write", toggle_proxy); toggle_proxy()

    btn_frame = ttk.Frame(frame); btn_frame.grid(row=8, column=0, columnspan=2, pady=(12,0))

    def on_save():
        uid_raw = e_user.get().strip()
        uid = re.sub(r"[^A-Za-z0-9_-]", "", uid_raw) or f"anon-{_rand()}"
        room = "lobby"  # 고정
        mode = mode_var.get()
        host = e_host.get().strip() or "127.0.0.1"
        try:
            port = int(e_port.get().strip() or "5555")
        except ValueError:
            messagebox.showerror("에러", "ZMQ_PORT는 정수여야 합니다.")
            return
        auto_focus = FOCUS_LABEL2VALUE[focus_var.get()]

        cfg = {
            "CONFIG_VERSION": 1,
            "USER_ID": uid,
            "ROOM_ID": room,
            "MODE": mode,
            "ZMQ_HOST": host,
            "ZMQ_PORT": port,
            "UDP_PORT": 5000,
            "BROADCAST_IP": "192.168.100.255",
            "TZ": "Asia/Seoul",
            "TOPMOST_DEFAULT": False,
            "TOPMOST_ON_NOTIFY": top_on.get(),
            "TOPMOST_ON_NOTIFY_MS": 3000,
            "AUTO_OPEN_DM": auto_dm.get(),
            "AUTO_FOCUS_ON_DM": auto_focus,
            "SOUND_ON_DM": True,
            "SEQ_GAP_WAIT_MS": 300,
            "LOG_LEVEL": "INFO",
        }

        # 1) 스키마 검증
        try:
            model = AppConfig(**cfg)
        except ValidationError as e:
            messagebox.showerror("검증 실패", str(e)); return

        # 2) 경로 준비 + 락 + 백업 + 원자적 저장
        path, bak, lock = config_paths()
        ensure_dir(path.parent)
        try:
            with FileLock(lock):
                backup(path, bak)
                atomic_write_yaml(path, model.model_dump())
        except Exception as e:
            messagebox.showerror("저장 실패", str(e)); return

        messagebox.showinfo("완료", f"설정 저장됨:\n{path}")
        root.result_model = model
        root.destroy()

    ttk.Button(btn_frame, text="저장 후 시작", command=on_save).pack(side="left", padx=4)
    ttk.Button(btn_frame, text="취소", command=root.destroy).pack(side="left", padx=4)

    root.result_model = None
    root.mainloop()
    return root.result_model
