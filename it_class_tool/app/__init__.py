# -*- coding: utf-8 -*-
"""界面层子包。

ChatApp 由多个 mixin 组合而成，按职责划分：
- ui.MainWindowMixin        窗口骨架、布局、会话列表、切换会话
- ui.HistoryMixin           历史记录读写、消息渲染、发送
- ui.EventsMixin            节点事件轮询、提示区
- ui.WindowMixin            焦点 / 置顶 / 任务栏闪烁
- ui.ToolboxMixin           工具箱（启动 CS、关闭极域）
"""
