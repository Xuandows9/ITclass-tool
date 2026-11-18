# -*- coding: utf-8 -*-
"""窗口焦点、置顶与任务栏闪烁。

收到新消息时尽量把窗口拉到前台；Windows 下用 AttachThreadInput 绕过
前台锁定，失败则退化为短暂置顶。
"""
import sys
import tkinter as tk


class WindowMixin:
    # ============================ 焦点 / 置顶 / 闪烁 ============================
    def _get_hwnd(self):
        if sys.platform != "win32":
            return 0
        try:
            import ctypes
        except Exception:
            return 0
        for getter in (lambda: int(self.root.frame(), 16),
                       lambda: int(self.root.winfo_id())):
            try:
                h = getter()
                if h:
                    top = ctypes.windll.user32.GetAncestor(h, 2)
                    return top or h
            except Exception:
                continue
        return 0

    def _force_foreground(self):
        if sys.platform != "win32":
            try:
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                return True
            except Exception:
                return False

        import ctypes
        user32 = ctypes.windll.user32
        kernel32 = ctypes.windll.kernel32

        hwnd = self._get_hwnd()
        if not hwnd:
            return False
        if user32.GetForegroundWindow() == hwnd:
            return True

        try:
            user32.ShowWindow(hwnd, 9)
        except Exception:
            pass

        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
        cur_thread = kernel32.GetCurrentThreadId()

        attached = False
        if fg_thread and fg_thread != cur_thread:
            try:
                attached = bool(user32.AttachThreadInput(cur_thread, fg_thread, True))
            except Exception:
                attached = False

        try:
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            try:
                self.root.focus_force()
            except Exception:
                pass
        finally:
            if attached:
                try:
                    user32.AttachThreadInput(cur_thread, fg_thread, False)
                except Exception:
                    pass

        return user32.GetForegroundWindow() == hwnd

    def _bring_to_front(self):
        if self._force_foreground():
            return
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.attributes("-topmost", True)
            self.root.focus_force()
        except Exception:
            pass
        if self._topmost_after_id is not None:
            try:
                self.root.after_cancel(self._topmost_after_id)
            except Exception:
                pass
        self._topmost_after_id = self.root.after(3000, self._clear_topmost)

    def _clear_topmost(self):
        self._topmost_after_id = None
        try:
            self.root.attributes("-topmost", False)
        except Exception:
            pass

    def _watch_focus_for_topmost(self):
        if self._topmost_after_id is not None and not self._is_window_active():
            try:
                self.root.after_cancel(self._topmost_after_id)
            except Exception:
                pass
            self._topmost_after_id = None
            try:
                self.root.attributes("-topmost", False)
            except Exception:
                pass
        self.root.after(200, self._watch_focus_for_topmost)

    def _is_window_active(self):
        if sys.platform == "win32":
            try:
                import ctypes
                fg = ctypes.windll.user32.GetForegroundWindow()
                hwnd = self._get_hwnd()
                return hwnd != 0 and fg == hwnd
            except Exception:
                pass
        try:
            focused = self.root.focus_displayof()
            if focused is None:
                return False
            try:
                return focused.winfo_toplevel() is self.root
            except Exception:
                return False
        except Exception:
            return True

    def _flash_conv(self, conv_id):
        self._pending_flash[conv_id] = 8
        if not self._flash_running:
            self._flash_running = True
            self.root.after(0, self._flash_tick)

    def _flash_tick(self):
        to_remove = []
        for conv_id, remain in list(self._pending_flash.items()):
            if remain <= 0:
                to_remove.append(conv_id)
                self._apply_flash_color(conv_id, on=False)
                continue
            self._apply_flash_color(conv_id, on=(remain % 2 == 0))
            self._pending_flash[conv_id] = remain - 1
        for c in to_remove:
            del self._pending_flash[c]
        if self._pending_flash:
            self.root.after(250, self._flash_tick)
        else:
            self._flash_running = False

    def _apply_flash_color(self, conv_id, on):
        lbl = self._conv_labels.get(conv_id)
        if lbl is None:
            return
        try:
            if on:
                lbl.configure(bg="#ff9800", fg="#ffffff")
            else:
                if conv_id == self.current_conv:
                    lbl.configure(bg="#d3e6ff", fg="#222")
                else:
                    is_online = getattr(lbl, "_is_online", True)
                    lbl.configure(bg="#ededed", fg="#222" if is_online else "#999")
        except tk.TclError:
            pass
