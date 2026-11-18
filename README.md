# it-class-tool

信息课小工具，包括局域网聊天、一键启动游戏、解除老师控制（关闭极域），不依赖网络

## 运行

```bash
python main.py
# 或
python -m it_class_tool
```

## 目录结构

```
main.py               源码运行入口（也是打包入口）
it_class_tool/
├── __init__.py       包出口：统一导出常量、类与函数
├── __main__.py       支持 python -m it_class_tool
├── config.py         全局常量（协议标识、端口、超时、字体、进程名等）
├── paths.py          运行时路径（data 目录、内置 CS1.6 目录）
├── cs.py             内置 CS1.6 的解压与定位
├── network.py        ChatNode：UDP 局域网发现 + TCP 私聊
├── main.py           启动入口 main()：DPI、昵称输入、解压、进入主窗口
└── app/              界面层
    ├── chat_app.py   ChatApp：组合下面的 mixin
    ├── main_window.py 窗口骨架、会话列表、切换会话
    ├── history.py   历史记录读写、消息渲染与发送
    ├── events.py    节点事件轮询、左下提示
    ├── window.py    焦点 / 置顶 / 闪烁
    └── toolbox.py   工具箱：启动 CS、关闭极域
```

运行时数据（聊天历史）与内置游戏解压目录仍在项目根：`data/`、`CS1_6/`。

## 配置

| 环境变量 | 作用 |
| --- | --- |
| `IT_CLASS_TOOL_DATA_DIR` | 自定义数据目录（默认项目根下的 `data/`） |

## 兼容性说明

协议标识为 `IT-CLASS-TOOL-V5`。改名前的旧版程序（标识 `LANCHAT-V5`）与新版本
在同一局域网内互相收不到对方，需各终端使用同一版本才能互相聊天。
