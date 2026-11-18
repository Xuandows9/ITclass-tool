# -*- coding: utf-8 -*-
"""左侧工具箱：启动内置 CS1.6、关闭极域电子教室。"""
import os
import subprocess
import sys
from tkinter import messagebox

from ..config import TARGET_PROCESSES, _CREATE_NO_WINDOW
from ..cs import cs_exe_path


class ToolboxMixin:
    # ============================ 工具箱功能 ============================
    def _cs_path_hint(self):
        p = cs_exe_path()
        if p:
            return "内置 CS1.6：" + os.path.basename(p)
        return "内置 CS1.6 未解压（重启程序会自动解压）"

    def _launch_cs(self):
        if sys.platform != "win32":
            messagebox.showinfo("提示", "该功能仅支持 Windows", parent=self.root)
            return
        path = cs_exe_path()
        if not path:
            messagebox.showerror("启动 CS 失败",
                                 "未找到内置 CS1.6 文件，请重新运行程序以解压。",
                                 parent=self.root)
            return
        try:
            exe_name = os.path.basename(path).lower()
            if exe_name == "hl.exe":
                args = [path, "-game", "cstrike"]
            else:
                args = [path]
            subprocess.Popen(args, cwd=os.path.dirname(path))
            self._show_notice(f"CS 已启动：{os.path.basename(path)}")
        except Exception as e:
            messagebox.showerror("启动 CS 失败", str(e), parent=self.root)

    def _kill_studentmain(self):
        if sys.platform != "win32":
            messagebox.showinfo("提示", "该功能仅支持 Windows", parent=self.root)
            return
        killed = []
        not_found = []
        failed = []
        for exe in TARGET_PROCESSES:
            try:
                r = subprocess.run(
                    ["taskkill", "/F", "/IM", exe],
                    capture_output=True, timeout=10,
                    creationflags=_CREATE_NO_WINDOW)
                if r.returncode == 0:
                    killed.append(exe)
                elif r.returncode == 128:
                    not_found.append(exe)
                else:
                    failed.append(exe)
            except Exception:
                failed.append(exe)
        if killed:
            self._show_notice(f"✅ 已关闭：{', '.join(killed)}")
        elif not_found and not failed:
            self._show_notice("极域未在运行（或已被关闭）")
        else:
            msg = ("无法关闭以下进程，可能权限不足：\n  " + ", ".join(failed) +
                   "\n\n建议：\n"
                   "1. 右键本程序 → 以管理员身份运行\n"
                   "2. 或按 Ctrl+Shift+Esc 打开任务管理器手动结束 StudentMain.exe")
            self._show_notice("⚠ 关闭极域失败，可能需要管理员权限")
            messagebox.showwarning("关闭极域失败", msg, parent=self.root)
