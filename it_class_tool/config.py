# -*- coding: utf-8 -*-
"""全局配置常量。

这里只放不依赖运行时路径的纯常量；需要计算目录的路径放在 paths.py。
"""
import sys

# ============================== 协议 / 网络 ==============================
# 协议标识：必须与对端一致才能互相发现，改名后与旧版 lanchat 互不兼容
APP_MAGIC = "IT-CLASS-TOOL-V5"
DISCOVERY_PORT = 37020
HEARTBEAT_INTERVAL = 2.5
PEER_TIMEOUT = 15.0

# ============================== 会话 / 界面 ==============================
GROUP_CONV = "__group__"
MAX_HISTORY = 1000
FONT = "Microsoft YaHei UI"

# 左下提示最多显示的行数：封顶后不会挤压用户列表，也不会越出窗口底部
HINT_MAX_LINES = 8

# ============================== 工具箱 ==============================
# 启动子进程时不弹出控制台窗口
_CREATE_NO_WINDOW = 0x08000000 if sys.platform == "win32" else 0

# 内置 CS1.6：打包时随 exe 一起嵌入，首次运行自动解压到程序同目录
CS_DIR_NAME = "CS1_6"
CS_EXE_NAMES = ("cs1.6.exe", "hl.exe")
CS_STAMP_NAME = ".extracted"

# 要关闭的极域进程名（主进程 + 常见守护进程），逐个用 taskkill /F /IM 进程名 结束
TARGET_PROCESSES = ["StudentMain.exe", "TopDomained.exe", "TopDomino.exe"]
