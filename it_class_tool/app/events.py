# -*- coding: utf-8 -*-
"""节点事件轮询与左下提示区。

后台网络线程只往 queue 里投事件，界面线程用 after() 周期取走，
避免在非主线程操作 tkinter。
"""
import queue
import time
import tkinter as tk

from ..config import GROUP_CONV, HINT_MAX_LINES


class EventsMixin:
    # ============================ 事件轮询 ============================
    def _poll_events(self):
        try:
            while True:
                ev, payload = self.q.get_nowait()
                if ev == "peers":
                    self._on_peers(payload)
                elif ev == "private":
                    self._on_private(payload)
                elif ev == "group":
                    self._on_group(payload)
                elif ev == "ack":
                    self._on_ack(payload)
                elif ev == "self_nick":
                    self.my_label.configure(text=f"我：{payload}")
                    self.root.title(f"局域网聊天 — {payload}")
                elif ev == "notice":
                    self._show_notice(payload)
        except queue.Empty:
            pass
        self.root.after(80, self._poll_events)

    def _on_peers(self, snapshot):
        self.peers = snapshot
        self._refresh_user_list()
        if self.current_conv != GROUP_CONV:
            peer = None
            for p in snapshot.values():
                if p["nick"] == self.current_conv:
                    peer = p
                    break
            if peer is None:
                self.title_label.configure(text=self.current_conv + "（离线）")
            elif peer.get("online"):
                self.title_label.configure(text=self.current_conv)
            else:
                self.title_label.configure(text=self.current_conv + "（离线）")
        if snapshot:
            self._set_hint("")

    def _on_private(self, msg):
        nick = str(msg.get("from_nick") or "未知")[:32]
        rec = {"nick": nick, "text": msg.get("content", ""),
               "direction": "in", "ts": msg.get("timestamp", time.time())}
        self.add_message(nick, rec)

        active = self._is_window_active()
        is_current = (nick == self.current_conv)

        if is_current:
            if not active:
                self._bring_to_front()
        else:
            self._show_notice(f"收到来自「{nick}」的新消息")
            if not active:
                self._bring_to_front()
                self.open_conversation(nick)
            else:
                self._flash_conv(nick)

    def _on_group(self, msg):
        nick = str(msg.get("from_nick") or "未知")[:32]
        rec = {"nick": nick, "text": msg.get("content", ""),
               "direction": "in", "ts": msg.get("timestamp", time.time())}
        self.add_message(GROUP_CONV, rec)

        active = self._is_window_active()
        is_current = (self.current_conv == GROUP_CONV)

        if is_current:
            if not active:
                self._bring_to_front()
        else:
            self._show_notice(f"群聊有新消息（来自「{nick}」）")
            if not active:
                self._bring_to_front()
                self.open_conversation(GROUP_CONV)
            else:
                self._flash_conv(GROUP_CONV)

    def _on_ack(self, msg):
        mid = msg.get("messageId")
        conv = self.pending.pop(mid, None)
        if not conv:
            return
        self._set_status(mid, "✓ 已送达", conv)

    def _show_notice(self, text):
        self._set_hint(text)

    def _set_hint(self, text):
        """设置左下提示：超过 HINT_MAX_LINES 行时封顶，避免挤压用户列表或越出窗口底部"""
        lbl = self.hint_label
        lbl.configure(text=text, height=0)
        if not text:
            return
        try:
            self.root.update_idletasks()
            line = int(self.root.tk.call("font", "metrics", lbl.cget("font"), "-linespace"))
            pad = 2 * int(lbl.cget("pady"))
        except (tk.TclError, ValueError):
            return
        if line > 0 and lbl.winfo_reqheight() > HINT_MAX_LINES * line + pad:
            lbl.configure(height=HINT_MAX_LINES)

    def _check_discovery_hint(self):
        if not self.peers:
            self._set_hint("未发现其他用户。\n"
                           "请检查：\n"
                           "1. 是否与对方在同一局域网\n"
                           "2. Windows 防火墙是否允许本程序通信\n"
                           "3. 是否有多台机器在同一网段")
