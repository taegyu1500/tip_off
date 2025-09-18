import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from app.core.state import AppState

class MainWindow:
    """
    - 좌: Notebook (Lobby + DM 탭)
    - 우: Roster (USER_ID 리스트)
    - 메시지 렌더: [시간] [이름] [채팅] 모두 좌측 정렬
      * Lobby: 이름=내 anon 닉(내 메시지), 상대 anon 닉(수신)
      * DM: 이름="me"(내 메시지), "@상대ID"(수신)
    """
    def __init__(self, root: tk.Tk, state: AppState,
                 send_lobby_cb: Callable[[str], None],
                 send_dm_cb: Callable[[str, str], None]):
        self.root = root
        self.state = state
        self.send_lobby_cb = send_lobby_cb
        self.send_dm_cb = send_dm_cb

        self.state.upsert_self()

        root.title(f"TIP-OFF — {state.user_id or 'anon'} @ {state.room_id}")
        root.geometry("1000x600")

        header = ttk.Frame(root, padding=(12,8)); header.pack(fill="x")
        ttk.Label(header, text="TIP-OFF", font=("Arial", 14, "bold")).pack(side="left")
        self.header_right = ttk.Label(header, text=f"room: {state.room_id}   anon: {state.anon_nick}", foreground="#666")
        self.header_right.pack(side="right")

        main = ttk.Frame(root); main.pack(fill="both", expand=True, padx=12, pady=(0,8))
        main.grid_columnconfigure(0, weight=4); main.grid_columnconfigure(1, weight=0)

        # ---- 좌: 채팅 탭 ----
        chat_wrap = ttk.Frame(main); chat_wrap.grid(row=0, column=0, sticky="nsew", padx=(0,12))
        self.nb = ttk.Notebook(chat_wrap); self.nb.pack(fill="both", expand=True)
        self.chat_tabs: Dict[Optional[str], Dict[str, Any]] = {}
        self._ensure_tab(None, title="Lobby")
        self.add_message("Welcome to TIP-OFF lobby. Type a message and press Enter.",
                         meta_hint=True, target=None)

        # ---- 우: 로스터 ----
        roster_wrap = ttk.Frame(main); roster_wrap.grid(row=0, column=1, sticky="ns")
        roster_wrap.grid_rowconfigure(1, weight=1)
        top_bar = ttk.Frame(roster_wrap); top_bar.grid(row=0, column=0, sticky="ew", pady=(0,4))
        self.roster_title = ttk.Label(top_bar, text="Roster (0)"); self.roster_title.pack(side="left")

        self.roster = ttk.Treeview(roster_wrap, columns=("user",), show="headings", height=20)
        self.roster.heading("user", text="User ID")
        self.roster.column("user", width=230, anchor="w")
        self.roster.grid(row=1, column=0, sticky="ns")
        self.roster.bind("<Double-1>", self._on_roster_dblclk)

        # ---- 입력 바 ----
        input_bar = ttk.Frame(root, padding=(12,8)); input_bar.pack(fill="x")
        self.entry = tk.Text(input_bar, height=3, wrap="word")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", self._on_return)
        self.entry.bind("<Shift-Return>", lambda e: self._insert_newline())
        ttk.Button(input_bar, text="Send", command=self.send_message).pack(side="left", padx=(8,0))

        self.close_btn = ttk.Button(input_bar, text="Close DM", command=self._close_active_dm)
        self.close_btn.pack(side="left", padx=(6,0))
        self._update_close_btn_state(target=None)
        self.root.bind_all("<Control-w>", self._close_active_dm_event)

        self._rclick_target: Optional[str] = None
        self.tab_menu = tk.Menu(self.nb, tearoff=0)
        self.tab_menu.add_command(label="Close DM", command=self._close_rclicked_dm)
        self.nb.bind("<Button-3>", self._on_tab_right_click)
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        self.refresh_roster()

    # ---------- 탭 유틸 ----------
    def _ensure_tab(self, target: Optional[str], title: Optional[str] = None):
        if target in self.chat_tabs:
            idx = self._index_of_tab(target)
            if idx is not None: self.nb.select(idx)
            return
        frame = ttk.Frame(self.nb)
        self.nb.add(frame, text=(title or (f"@{target}" if target else "Lobby")))
        self.nb.select(self.nb.index("end") - 1)
        canvas = tk.Canvas(frame, highlightthickness=0)
        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=canvas.yview)
        msg_frame = ttk.Frame(canvas)
        msg_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0,0), window=msg_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.chat_tabs[target] = {"frame": frame, "canvas": canvas, "msg_frame": msg_frame, "scrollbar": scrollbar}

    def _index_of_tab(self, target: Optional[str]) -> Optional[int]:
        if target not in self.chat_tabs: return None
        frame = self.chat_tabs[target]["frame"]
        tabs = self.nb.tabs()
        for idx, tab_id in enumerate(tabs):
            if tab_id == str(frame): return idx
        return None

    def _target_for_index(self, idx: int) -> Optional[str]:
        tabs = self.nb.tabs()
        if idx < 0 or idx >= len(tabs): return None
        tab_id = tabs[idx]
        for target, parts in self.chat_tabs.items():
            if str(parts["frame"]) == tab_id: return target
        return None

    def _active_target(self) -> Optional[str]:
        current = self.nb.select()
        for target, parts in self.chat_tabs.items():
            if str(parts["frame"]) == current:
                return target
        return None

    def _view_for(self, target: Optional[str]) -> Dict[str, Any]:
        self._ensure_tab(target)
        return self.chat_tabs[target]

    # ---------- 입력/전송 ----------
    def _insert_newline(self):
        self.entry.insert("insert", "\n"); return "break"
    def _on_return(self, event):
        self.send_message(); return "break"

    def send_message(self):
        text = self.entry.get("1.0", "end").strip()
        if not text: return
        target = self._active_target()  # None=lobby, or user_id
        if target is None:
            self.send_lobby_cb(text)
            self.add_message(text, mine=True, target=None)
        else:
            # DM: 상대 라우팅은 메인에서 처리(콜백으로 위임)
            self.send_dm_cb(target, text)
            self.add_message(text, mine=True, target=target)
        self.entry.delete("1.0", "end")

    # ---------- 메시지 렌더 (시간 · 이름 · 채팅) ----------
    def add_message(self, text: str, mine: bool = False, meta_hint: bool=False,
                    target: Optional[str] = None, meta_nick: Optional[str] = None,
                    from_uid: Optional[str] = None, is_history: bool = False):
        view = self._view_for(target)
        row = ttk.Frame(view["msg_frame"]); row.pack(fill="x", anchor="w", pady=3)

        if meta_hint:
            hhmm, name = "--:--", "tips"
        else:
            hhmm = datetime.now().strftime("%H:%M")
            if target is None:
                # Lobby: 내 메시지는 내 anon, 수신은 상대 anon(meta_nick)
                name = meta_nick if (meta_nick and not mine) else self.state.anon_nick
            else:
                # DM: 내 메시지는 'me', 수신은 '@상대ID'
                name = "me" if mine else (f"@{from_uid}" if from_uid else "@peer")

        # 히스토리 메시지 표시
        if is_history:
            name = f"[히스토리] {name}"

        # [시간]
        time_color = "#999" if is_history else "#666"
        t_lbl = ttk.Label(row, text=hhmm, width=6, anchor="w", foreground=time_color)
        t_lbl.grid(row=0, column=0, sticky="w")

        # [이름]
        name_color = "#888" if is_history else "#444"
        name_font = ("Arial", 9, "italic") if is_history else (("Arial", 10, "bold") if not meta_hint else ("Arial", 10))
        n_lbl = ttk.Label(row, text=name, width=15, anchor="w", font=name_font, foreground=name_color)
        n_lbl.grid(row=0, column=1, sticky="w", padx=(6,8))

        # [채팅]
        text_color = "#777" if is_history else "black"
        c_lbl = ttk.Label(row, text=text, wraplength=680, justify="left", foreground=text_color)
        c_lbl.grid(row=0, column=2, sticky="w")

        row.grid_columnconfigure(0, weight=0)
        row.grid_columnconfigure(1, weight=0)
        row.grid_columnconfigure(2, weight=1)

        self.root.after(10, lambda: view["canvas"].yview_moveto(1.0))

    # ---------- 로스터 ----------
    def refresh_roster(self):
        for iid in self.roster.get_children(): self.roster.delete(iid)
        count = 0
        for entry in self.state.list_roster():
            label = entry.user_id + (" (me)" if entry.is_self else "")
            self.roster.insert("", "end", values=(label,)); count += 1
        self.roster_title.config(text=f"Roster ({count})")

    def _on_roster_dblclk(self, _event):
        sel = self.roster.selection()
        if not sel: return
        label = self.roster.item(sel[0], "values")[0]
        user_id = label.replace(" (me)", "")
        if user_id == self.state.user_id: return
        self.state.ensure_dm_session(user_id)
        self._ensure_tab(user_id)
        self.entry.focus_set()

    # ---------- 닫기 ----------
    def _close_active_dm(self):
        target = self._active_target()
        if target is None: return
        self._close_dm_tab(target)
    def _close_active_dm_event(self, event):
        self._close_active_dm(); return "break"
    def _on_tab_changed(self, _event):
        target = self._active_target()
        if target is None:
            self.header_right.config(text=f"room: {self.state.room_id}   anon: {self.state.anon_nick}")
        else:
            self.header_right.config(text=f"DM to @{target}")
        self._update_close_btn_state(target)
    def _update_close_btn_state(self, target: Optional[str]):
        self.close_btn.state(["disabled"] if target is None else ["!disabled"])
    def _on_tab_right_click(self, event):
        try: idx = self.nb.index(f"@{event.x},{event.y}")
        except Exception: return
        target = self._target_for_index(idx)
        if target is None: return
        self._rclick_target = target
        try: self.tab_menu.tk_popup(event.x_root, event.y_root)
        finally: self.tab_menu.grab_release()
    def _close_rclicked_dm(self):
        if getattr(self, "_rclick_target", None) is None: return
        self._close_dm_tab(self._rclick_target); self._rclick_target = None
    def _close_dm_tab(self, target: str):
        parts = self.chat_tabs.pop(target, None)
        if parts: self.nb.forget(parts["frame"])
        lobby_idx = self._index_of_tab(None)
        if lobby_idx is not None: self.nb.select(lobby_idx)
        self._on_tab_changed(None)
