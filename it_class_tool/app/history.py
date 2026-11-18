# -*- coding: utf-8 -*-
"""历史记录、消息渲染与发送。

会话以会话键 conv_id 区分：群聊用 GROUP_CONV，私聊直接用对方昵称。
历史按会话各存一个 JSON 文件，最多保留 MAX_HISTORY 条。
"""
import json
import os
import time
import uuid

from ..config import GROUP_CONV, MAX_HISTORY
from ..paths import HISTORY_DIR


class HistoryMixin:
    # ============================ 历史记录 ============================
    def _conv_file(self, conv_id):
        safe = "".join(c if (c.isalnum() or c in "-_") else "_" for c in conv_id)
        return os.path.join(HISTORY_DIR, safe + ".json")

    def load_history(self, conv_id):
        if conv_id in self.histories:
            return self.histories[conv_id]
        data = []
        try:
            with open(self._conv_file(conv_id), "r", encoding="utf-8") as f:
                obj = json.load(f)
            if isinstance(obj, list):
                data = obj
        except (OSError, ValueError):
            data = []
        self.histories[conv_id] = data
        return data

    def save_history(self, conv_id):
        data = self.histories.get(conv_id, [])[-MAX_HISTORY:]
        self.histories[conv_id] = data
        try:
            with open(self._conv_file(conv_id), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
        except OSError:
            pass

    def add_message(self, conv_id, rec):
        hist = self.load_history(conv_id)
        hist.append(rec)
        if len(hist) > MAX_HISTORY:
            del hist[:len(hist) - MAX_HISTORY]
        self.save_history(conv_id)
        if conv_id == self.current_conv:
            self._render_rec(rec)
            self.chat_area.see("end")

    # ============================ 渲染 ============================
    def _append_text(self, text, *tags):
        self.chat_area.configure(state="normal")
        self.chat_area.insert("end", text, tags if tags else ())
        self.chat_area.configure(state="disabled")

    def _render_rec(self, rec):
        direction = rec.get("direction")
        if direction == "sys":
            self._append_text("      " + rec.get("text", "") + "\n\n", "sys")
            return
        ts = rec.get("ts") or time.time()
        tstr = time.strftime("%H:%M:%S", time.localtime(ts))
        tag = "me" if direction == "out" else "peer"
        self._append_text(f"{rec.get('nick', '')}   {tstr}\n", "meta")
        self._append_text(rec.get("text", "") + "\n", tag)
        mid = rec.get("mid")
        if mid and direction == "out":
            self._append_text(rec.get("status", "") + "\n", f"st_{mid}", "meta")
        self._append_text("\n")

    def _render_all(self):
        self.chat_area.configure(state="normal")
        self.chat_area.delete("1.0", "end")
        self.chat_area.configure(state="disabled")
        for rec in self.load_history(self.current_conv):
            self._render_rec(rec)
        self.chat_area.see("end")

    def _set_status(self, mid, status_text, conv_id):
        for rec in self.histories.get(conv_id, []):
            if rec.get("mid") == mid:
                rec["status"] = status_text
        self.save_history(conv_id)
        if conv_id != self.current_conv:
            return
        r = self.chat_area.tag_ranges(f"st_{mid}")
        if not r:
            return
        self.chat_area.configure(state="normal")
        self.chat_area.delete(r[0], r[1])
        self.chat_area.insert(r[0], status_text, (f"st_{mid}", "meta"))
        self.chat_area.configure(state="disabled")

    # ============================ 发送 ============================
    def _on_enter(self, event):
        self.send_current()
        return "break"

    def _on_shift_enter(self, event):
        self.input_box.insert("insert", "\n")
        return "break"

    def _uid_for_nick(self, nick):
        for uid, p in self.peers.items():
            if p["nick"] == nick:
                return uid
        return None

    def send_current(self):
        text = self.input_box.get("1.0", "end").strip()
        if not text:
            return
        self.input_box.delete("1.0", "end")
        conv = self.current_conv

        if conv == GROUP_CONV:
            self.node.send_group(text)
            self.add_message(conv, {"nick": "我", "text": text, "direction": "out",
                                    "ts": time.time(), "status": ""})
            return

        uid = self._uid_for_nick(conv)
        if not uid:
            self.add_message(conv, {"nick": "系统", "text": "对方不在线，消息未发送",
                                    "direction": "sys", "ts": time.time()})
            return

        peer = self.peers.get(uid)
        if not peer or not peer.get("online"):
            self.add_message(conv, {"nick": "系统", "text": "对方已离线，消息未发送",
                                    "direction": "sys", "ts": time.time()})
            return

        mid = uuid.uuid4().hex
        rec = {"nick": "我", "text": text, "direction": "out",
               "ts": time.time(), "mid": mid, "status": "⏳ 发送中"}
        self.pending[mid] = conv
        self.add_message(conv, rec)
        ok, err = self.node.send_private(uid, text, mid)
        if ok:
            return
        self.pending.pop(mid, None)
        self._set_status(mid, "✗ " + (err or "发送失败"), conv)
