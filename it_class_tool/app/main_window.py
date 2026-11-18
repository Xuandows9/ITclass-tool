# -*- coding: utf-8 -*-
"""主窗口：布局、会话列表、切换会话。

所有 tkinter 控件都直接挂在 self 上（例如 self.input_box、self.chat_area），
与拆分前单文件版本中的控件命名保持一致，方便各个 mixin 共享。
"""
import tkinter as tk
from tkinter import scrolledtext

from ..config import FONT, GROUP_CONV


class MainWindowMixin:
    # ============================ UI 构建 ============================
    def _build_ui(self):
        self.root.geometry("1080x680")
        self.root.configure(bg="#f5f5f5")
        self.root.minsize(860, 540)

        # ---------- 左侧 ----------
        left = tk.Frame(self.root, width=230, bg="#ededed")
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        top = tk.Frame(left, bg="#dfdfdf")
        top.pack(fill="x")
        self.my_label = tk.Label(top, text=f"我：{self.node.nick}", anchor="w",
                                 font=(FONT, 11, "bold"), bg="#dfdfdf",
                                 fg="#333", padx=12, pady=10)
        self.my_label.pack(fill="x")

        # ---------- 工具箱 ----------
        toolbox = tk.Frame(left, bg="#ededed")
        toolbox.pack(fill="x", padx=8, pady=(8, 4))

        tk.Label(toolbox, text="工具箱", anchor="w", font=(FONT, 9, "bold"),
                 bg="#ededed", fg="#666").pack(fill="x", pady=(0, 4))

        self.cs_btn = tk.Button(toolbox, text="启动 CS", command=self._launch_cs,
                                font=(FONT, 10, "bold"), bg="#4a90e2", fg="white",
                                activebackground="#3a7ac9", activeforeground="white",
                                relief="flat", cursor="hand2", pady=5)
        self.cs_btn.pack(fill="x", pady=2)

        self.cs_path_label = tk.Label(toolbox, text=self._cs_path_hint(), anchor="w",
                                      font=(FONT, 8), bg="#ededed", fg="#888",
                                      wraplength=214, justify="left")
        self.cs_path_label.pack(fill="x", pady=(0, 4))

        self.kill_btn = tk.Button(toolbox, text="关闭极域", command=self._kill_studentmain,
                                  font=(FONT, 10, "bold"), bg="#e94b3c", fg="white",
                                  activebackground="#c93a2c", activeforeground="white",
                                  relief="flat", cursor="hand2", pady=5)
        self.kill_btn.pack(fill="x", pady=2)

        self.hint_sep = tk.Frame(left, height=1, bg="#d5d5d5")
        self.hint_sep.pack(fill="x", padx=8, pady=(6, 4))

        # ---------- 左下提示（先于列表 pack：空间不足时收缩列表，保证提示完整可见） ----------
        self.hint_label = tk.Label(left, text="", anchor="w", justify="left",
                                   font=(FONT, 9), bg="#ededed", fg="#c0392b",
                                   wraplength=210, padx=10, pady=6)
        self.hint_label.pack(fill="x", side="bottom")

        # ---------- 会话列表 ----------
        wrap = tk.Frame(left, bg="#ededed")
        wrap.pack(fill="both", expand=True)
        self.canvas = tk.Canvas(wrap, bg="#ededed", highlightthickness=0)
        vsb = tk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.list_frame = tk.Frame(self.canvas, bg="#ededed")
        self.canvas.create_window((0, 0), window=self.list_frame, anchor="nw", tags="inner")
        self.list_frame.bind("<Configure>",
                             lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>",
                         lambda e: self.canvas.itemconfig("inner", width=e.width))

        # ---------- 右侧 ----------
        right = tk.Frame(self.root, bg="#f7f7f7")
        right.pack(side="left", fill="both", expand=True)

        self.title_label = tk.Label(right, text="群聊（所有人）", anchor="w",
                                    font=(FONT, 12, "bold"), bg="#ffffff",
                                    fg="#222", padx=16, pady=10)
        self.title_label.pack(side="top", fill="x")

        self.bottom = tk.Frame(right, bg="#ffffff", height=88)
        self.bottom.pack(side="bottom", fill="x")
        self.bottom.pack_propagate(False)

        self.send_btn = tk.Button(self.bottom, text="发送", command=self.send_current,
                                  font=(FONT, 11), bg="#07c160", fg="white",
                                  activebackground="#06a94f", relief="flat",
                                  width=8, cursor="hand2")
        self.send_btn.pack(side="right", padx=(0, 12), pady=8)

        self.input_box = tk.Text(self.bottom, height=2, font=(FONT, 11),
                                 relief="flat", bg="#ffffff", fg="#000000",
                                 padx=10, pady=8, wrap="word",
                                 insertbackground="black")
        self.input_box.pack(side="left", fill="both", expand=True, padx=(10, 6), pady=8)
        self.input_box.bind("<Return>", self._on_enter)
        self.input_box.bind("<Shift-Return>", self._on_shift_enter)

        self.chat_area = scrolledtext.ScrolledText(
            right, state="disabled", wrap="word", font=(FONT, 11),
            bg="#f7f7f7", relief="flat", padx=16, pady=10,
            spacing1=2, spacing3=3, height=6)
        self.chat_area.pack(side="top", fill="both", expand=True)
        self.chat_area.tag_configure("meta", foreground="#8a8a8a", font=(FONT, 9))
        self.chat_area.tag_configure("me", foreground="#1a7f37", font=(FONT, 11))
        self.chat_area.tag_configure("peer", foreground="#1f4e9c", font=(FONT, 11))
        self.chat_area.tag_configure("sys", foreground="#b45309", font=(FONT, 9))

        self._refresh_user_list()
        self.root.after(200, lambda: self.input_box.focus_set())

    # ============================ 会话列表 ============================
    def _refresh_user_list(self):
        for w in self.list_frame.winfo_children():
            w.destroy()
        self._conv_labels = {}

        self._add_item(GROUP_CONV, "群聊（所有人）", "👥", online=True)
        tk.Frame(self.list_frame, height=1, bg="#d5d5d5").pack(fill="x", padx=10, pady=4)

        online_peers = sorted([p for p in self.peers.values() if p.get("online")],
                              key=lambda p: p["nick"])
        offline_peers = sorted([p for p in self.peers.values() if not p.get("online")],
                               key=lambda p: p["nick"])

        if not online_peers and not offline_peers:
            tk.Label(self.list_frame, text="（暂无其他用户）", anchor="w",
                     font=(FONT, 9), bg="#ededed", fg="#999",
                     padx=12, pady=8).pack(fill="x")
            return

        for p in online_peers:
            self._add_item(p["nick"], p["nick"], "●", online=True)

        if offline_peers:
            if online_peers:
                tk.Frame(self.list_frame, height=1, bg="#d5d5d5").pack(
                    fill="x", padx=10, pady=3)
            for p in offline_peers:
                self._add_item(p["nick"], p["nick"], "○", online=False)

    def _add_item(self, conv_id, text, prefix, online=True):
        active = (conv_id == self.current_conv)
        bg = "#d3e6ff" if active else "#ededed"
        fg = "#222" if online else "#999"
        label_text = f"{prefix} {text}"
        if not online and conv_id != GROUP_CONV:
            label_text += "（离线）"
        lbl = tk.Label(self.list_frame, text=label_text, anchor="w",
                       bg=bg, fg=fg, font=(FONT, 11),
                       padx=12, pady=9, cursor="hand2")
        lbl.pack(fill="x", padx=4, pady=1)
        self._conv_labels[conv_id] = lbl
        setattr(lbl, "_is_online", online)
        lbl.bind("<Button-1>", lambda e, c=conv_id: self.open_conversation(c))
        if online:
            lbl.bind("<Enter>", lambda e, l=lbl, c=conv_id:
                     l.configure(bg="#e2e2e2") if c != self.current_conv else None)
            lbl.bind("<Leave>", lambda e, l=lbl, c=conv_id:
                     l.configure(bg="#d3e6ff" if c == self.current_conv else "#ededed"))

    def open_conversation(self, conv_id):
        if conv_id in self._pending_flash:
            self._pending_flash.pop(conv_id, None)
            self._apply_flash_color(conv_id, on=False)

        self.current_conv = conv_id
        if conv_id == GROUP_CONV:
            self.title_label.configure(text="群聊（所有人）")
        else:
            peer = None
            for p in self.peers.values():
                if p["nick"] == conv_id:
                    peer = p
                    break
            if peer is None:
                self.title_label.configure(text=conv_id + "（离线）")
            elif peer.get("online"):
                self.title_label.configure(text=conv_id)
            else:
                self.title_label.configure(text=conv_id + "（离线）")
        self._refresh_user_list()
        self._render_all()
        self.input_box.focus_set()
