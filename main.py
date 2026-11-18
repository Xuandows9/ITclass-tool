#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""it-class-tool — 信息课小工具

包含：局域网聊天、一键启动内置 CS1.6、一键关闭极域电子教室。
纯 P2P，无独立服务端，不依赖外网。

这是源码运行入口，实际实现位于同目录的 it_class_tool/ 包中：
直接运行  python main.py  即可，入口与打包方式保持不变。
"""
from it_class_tool import *          # noqa: F401,F403 —— 保持模块级符号可见
from it_class_tool import main

if __name__ == "__main__":
    main()
