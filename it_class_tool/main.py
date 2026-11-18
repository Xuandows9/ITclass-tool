# -*- coding: utf-8 -*-
"""启动入口：DPI 适配、昵称输入、CS 解压、进入主窗口。"""
import os
import socket
import sys
import tkinter as tk
import uuid
from tkinter import messagebox

from .app.chat_app import ChatApp
from .config import FONT
from .cs import cs_exe_path, cs_ready, extract_cs
from .paths import CS_BUNDLE_DIR, CS_DIR


def default_nick():
    try:
        h = socket.gethostname()
        return h[:12] if h else "同学" + uuid.uuid4().hex[:3]
    except Exception:
        return "同学" + uuid.uuid4().hex[:3]


def ask_nickname_in_root(root):
    for w in root.winfo_children():
        w.destroy()
    root.title("局域网聊天工具")
    root.geometry("400x220")
    root.resizable(False, False)
    root.configure(bg="#f7f7f7")

    state: dict = {"nick": None}
    done_var = tk.BooleanVar(root, False)

    tk.Label(root, text="请输入你的昵称", font=(FONT, 13, "bold"),
             bg="#f7f7f7", fg="#222").pack(pady=(26, 12))

    var = tk.StringVar(value=default_nick())
    entry = tk.Entry(root, textvariable=var, font=(FONT, 12),
                     justify="center", relief="flat", bg="#ffffff")
    entry.pack(padx=40, fill="x", ipady=7)
    entry.focus_set()
    entry.select_range(0, "end")

    def submit(event=None):
        n = var.get().strip()
        if not n:
            messagebox.showwarning("提示", "昵称不能为空", parent=root)
            return
        state["nick"] = n[:16]
        done_var.set(True)

    tk.Button(root, text="进入聊天", command=submit, font=(FONT, 11),
              bg="#07c160", fg="white", relief="flat", width=14,
              cursor="hand2").pack(pady=18)
    root.bind("<Return>", submit)

    def on_close():
        state["nick"] = None
        done_var.set(True)
    root.protocol("WM_DELETE_WINDOW", on_close)

    root.update_idletasks()
    root.deiconify()
    root.lift()
    root.focus_force()

    try:
        root.wait_variable(done_var)
    except tk.TclError:
        pass
    root.unbind("<Return>")
    return state["nick"]


def prepare_bundled_cs(root):
    """启动时把嵌入的 CS1.6 解压到程序同目录；已解压则直接复用"""
    if os.path.abspath(CS_BUNDLE_DIR) == os.path.abspath(CS_DIR) or cs_ready():
        return cs_exe_path()

    label = None
    try:
        for w in root.winfo_children():
            w.destroy()
        root.title("局域网聊天工具")
        root.geometry("440x150")
        root.resizable(False, False)
        root.configure(bg="#f7f7f7")
        label = tk.Label(root, text="首次运行，正在解压内置 CS1.6…",
                         font=(FONT, 12), bg="#f7f7f7", fg="#222")
        label.pack(expand=True)
        root.deiconify()
        root.lift()
        root.update()
    except tk.TclError:
        label = None

    def on_progress(done, total):
        if label is None:
            return
        try:
            label.configure(text=f"正在解压内置 CS1.6：{done}/{total}")
            root.update()
        except tk.TclError:
            pass

    try:
        return extract_cs(on_progress)
    except OSError as e:
        try:
            messagebox.showerror(
                "解压 CS1.6 失败",
                f"{e}\n\n请把程序放到有写入权限的目录后重新运行。",
                parent=root)
        except tk.TclError:
            pass
        return None


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

    try:
        root = tk.Tk()
    except Exception as e:
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, f"Tk 初始化失败：{e}", "it-class-tool", 0x10)
        except Exception:
            print(f"Tk 初始化失败：{e}")
        return

    cs_path = prepare_bundled_cs(root)

    try:
        nick = ask_nickname_in_root(root)
        if not nick:
            root.destroy()
            return

        for w in root.winfo_children():
            w.destroy()
        root.resizable(True, True)
        root.protocol("WM_DELETE_WINDOW", root.destroy)

        app = ChatApp(root, nick)
        if cs_path is None:
            app._show_notice("⚠ 内置 CS1.6 未解压，无法启动 CS")
        root.deiconify()
        root.lift()
        root.mainloop()
    except Exception:
        import traceback
        tb = traceback.format_exc()
        try:
            messagebox.showerror("启动失败", tb[:1500])
        except Exception:
            print(tb)
        raise
