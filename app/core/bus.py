"""
EventBus: 네트워크 스레드가 발생시키는 이벤트를 Tk 메인스레드에서 안전하게 처리하기 위한 큐 기반 브릿지.
- post(evt, **payload): 어느 스레드에서든 호출 가능
- on(evt, handler): 메인스레드에서 실행될 핸들러 등록
- start(): Tk after로 주기 폴링 시작
"""
from __future__ import annotations
import queue
from typing import Callable, Dict, List

class EventBus:
    def __init__(self, root):
        self.root = root
        self.q: "queue.Queue[tuple[str, dict]]" = queue.Queue()
        self.handlers: Dict[str, List[Callable[[dict], None]]] = {}
        self._stopped = False

    def on(self, evt: str, handler: Callable[[dict], None]) -> None:
        self.handlers.setdefault(evt, []).append(handler)

    def post(self, evt: str, **payload) -> None:
        self.q.put((evt, payload))

    def _pump_once(self) -> None:
        # 큐에 쌓인 이벤트를 모두 비우고 순서대로 핸들러 호출
        while True:
            try:
                evt, payload = self.q.get_nowait()
            except queue.Empty:
                break
            for h in self.handlers.get(evt, []):
                try:
                    h(payload)
                except Exception as e:
                    print(f"[bus] handler error on {evt}: {e}")

    def pump(self) -> None:
        if self._stopped:
            return
        self._pump_once()
        # 50ms마다 한 번씩 폴링 (UI가 끊김 없음)
        self.root.after(50, self.pump)

    def start(self) -> None:
        self._stopped = False
        self.root.after(50, self.pump)

    def stop(self) -> None:
        self._stopped = True
