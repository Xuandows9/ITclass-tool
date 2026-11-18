# -*- coding: utf-8 -*-
"""ChatApp：把网络节点与各界面 mixin 组装成完整界面。"""
import queue

from ..config import GROUP_CONV
from ..network import ChatNode
from .events import EventsMixin
from .history import HistoryMixin
from .main_window import MainWindowMixin
from .toolbox import ToolboxMixin
from .window import WindowMixin


class ChatApp(MainWindowMixin, ToolboxMixin, HistoryMixin,
              EventsMixin, WindowMixin):
    def __init__(self, root, nick):
        self.root = root
        self.q = queue.Queue()
        self.node = ChatNode(nick, self.q)
        self.current_conv = GROUP_CONV
        self.histories = {}
        self.pending = {}
        self.peers = {}

        self._pending_flash = {}
        self._flash_running = False
        self._conv_labels = {}
        self._topmost_after_id = None

        self._build_ui()
        self.node.start()
        self.root.title(f"局域网聊天 — {self.node.nick}")
        self.root.after(80, self._poll_events)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.after(12000, self._check_discovery_hint)
        self.root.after(200, self._watch_focus_for_topmost)

    def _on_close(self):
        try:
            self.node.stop()
        finally:
            self.root.destroy()
