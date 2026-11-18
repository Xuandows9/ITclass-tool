# -*- coding: utf-8 -*-
"""it-class-tool — 信息课小工具（局域网聊天，纯 P2P，无独立服务端）。

v5 新增：
- 左侧工具箱：一键启动内置 CS1.6（随 exe 嵌入，首次运行自动解压到程序同目录）
- 左侧工具箱：一键关闭极域电子教室（taskkill /F /IM 进程名）

模块划分：
    config    全局常量（端口、超时、字体、进程名等）
    paths     运行时路径（数据目录、内置 CS 目录）
    cs        内置 CS1.6 的解压与定位
    network   ChatNode：UDP 发现 + TCP 私聊
    app/      界面层（ChatApp 由若干 mixin 组合而成）
    main      启动入口 main()

源码运行的入口是项目根目录下的 main.py。
"""
from .app.chat_app import ChatApp
from .config import (
    APP_MAGIC,
    CS_DIR_NAME,
    CS_EXE_NAMES,
    CS_STAMP_NAME,
    DISCOVERY_PORT,
    FONT,
    GROUP_CONV,
    HEARTBEAT_INTERVAL,
    HINT_MAX_LINES,
    MAX_HISTORY,
    PEER_TIMEOUT,
    TARGET_PROCESSES,
    _CREATE_NO_WINDOW,
)
from .cs import _copy_file, cs_exe_path, cs_ready, extract_cs
from .main import ask_nickname_in_root, default_nick, main, prepare_bundled_cs
from .network import ChatNode
from .paths import (
    BASE_DIR,
    BUNDLE_DIR,
    CS_BUNDLE_DIR,
    CS_DIR,
    DATA_DIR,
    HISTORY_DIR,
    base_dir,
)

__version__ = "5.0"

__all__ = [
    # 版本
    "__version__",
    # 配置
    "APP_MAGIC", "DISCOVERY_PORT", "HEARTBEAT_INTERVAL", "PEER_TIMEOUT",
    "GROUP_CONV", "MAX_HISTORY", "FONT", "_CREATE_NO_WINDOW",
    "HINT_MAX_LINES", "TARGET_PROCESSES",
    "CS_DIR_NAME", "CS_EXE_NAMES", "CS_STAMP_NAME",
    # 路径
    "base_dir", "BASE_DIR", "DATA_DIR", "HISTORY_DIR",
    "BUNDLE_DIR", "CS_DIR", "CS_BUNDLE_DIR",
    # 内置 CS
    "cs_exe_path", "cs_ready", "extract_cs", "_copy_file",
    # 网络 / 界面
    "ChatNode", "ChatApp",
    # 入口
    "default_nick", "ask_nickname_in_root", "prepare_bundled_cs", "main",
]
