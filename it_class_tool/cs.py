# -*- coding: utf-8 -*-
"""内置 CS1.6 的解压与定位。

打包时 CS1_6 目录随 exe 一起嵌入（PyInstaller 的 data），首次运行时解压到程序同目录。
"""
import os
import sys

from .config import APP_MAGIC, CS_EXE_NAMES, CS_STAMP_NAME
from .paths import CS_BUNDLE_DIR, CS_DIR


def cs_exe_path():
    """返回内置 CS1.6 启动程序的完整路径；未解压或缺失时返回 None"""
    for name in CS_EXE_NAMES:
        p = os.path.join(CS_DIR, name)
        if os.path.isfile(p):
            return p
    return None


def cs_ready():
    return os.path.isfile(os.path.join(CS_DIR, CS_STAMP_NAME)) and \
        cs_exe_path() is not None


def _copy_file(src, dst):
    """复制文件并保留时间戳/只读属性；Windows 走系统 API，失败或其它平台走分块复制"""
    if os.path.exists(dst):
        try:
            os.chmod(dst, 0o666)          # 清掉只读，允许覆盖上次残留的文件
        except OSError:
            pass
    done = False
    if sys.platform == "win32":
        try:
            import ctypes
            done = bool(ctypes.windll.kernel32.CopyFileW(src, dst, False))
        except Exception:
            done = False
    if not done:
        with open(src, "rb") as fs, open(dst, "wb") as fd:
            while True:
                chunk = fs.read(1 << 20)
                if not chunk:
                    break
                fd.write(chunk)
    try:
        st = os.stat(src)
        os.chmod(dst, st.st_mode)
        os.utime(dst, (st.st_atime, st.st_mtime))
    except OSError:
        pass


def extract_cs(progress=None):
    """把嵌入的 CS1_6 解压到程序同目录，返回启动程序路径；失败抛 OSError"""
    if os.path.abspath(CS_BUNDLE_DIR) == os.path.abspath(CS_DIR):
        return cs_exe_path()
    if cs_ready():
        return cs_exe_path()
    if not os.path.isdir(CS_BUNDLE_DIR):
        return None

    stamp = os.path.join(CS_DIR, CS_STAMP_NAME)
    try:
        os.remove(stamp)
    except OSError:
        pass

    items = []
    for dirpath, _dirnames, filenames in os.walk(CS_BUNDLE_DIR):
        for name in filenames:
            src = os.path.join(dirpath, name)
            items.append((src, os.path.join(CS_DIR, os.path.relpath(src, CS_BUNDLE_DIR))))

    os.makedirs(CS_DIR, exist_ok=True)
    for i, (src, dst) in enumerate(items, 1):
        parent = os.path.dirname(dst)
        if parent:
            os.makedirs(parent, exist_ok=True)
        _copy_file(src, dst)
        if progress is not None and (i % 200 == 0 or i == len(items)):
            progress(i, len(items))

    # 全部复制成功后才写标记，中断时下次启动会重新解压
    with open(stamp, "w", encoding="utf-8") as f:
        f.write(f"{APP_MAGIC}\n{len(items)}\n")
    return cs_exe_path()
