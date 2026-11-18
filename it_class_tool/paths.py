# -*- coding: utf-8 -*-
"""运行时路径。

程序的"工作根目录"取决于怎么运行：
- PyInstaller 打包运行：exe 所在目录
- 源码运行：本文件位于 <项目根>/it_class_tool/paths.py，因此项目根是上两级目录

这样拆分包之后，data 目录和内置 CS1.6 解压目录仍然落在项目根目录下，
与拆分前的单文件版本完全一致。
"""
import os
import sys

from .config import CS_DIR_NAME


def base_dir():
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    # __file__ = <项目根>/it_class_tool/paths.py
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


BASE_DIR = base_dir()
DATA_DIR = os.environ.get("IT_CLASS_TOOL_DATA_DIR") or os.path.join(BASE_DIR, "data")
HISTORY_DIR = os.path.join(DATA_DIR, "history")

# 嵌入资源根目录：onefile 打包时为 PyInstaller 的临时解包目录，源码运行时为项目根目录
BUNDLE_DIR = getattr(sys, "_MEIPASS", BASE_DIR)
CS_DIR = os.path.join(BASE_DIR, CS_DIR_NAME)
CS_BUNDLE_DIR = os.path.join(BUNDLE_DIR, CS_DIR_NAME)
