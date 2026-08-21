# AIWorkbench

一个**本地优先、完全开源**的桌面 AI 工作台。你可以创建多个独立「空间（Space）」，每个空间拥有独立的对话、知识图谱记忆和配置。

> 技术栈：Python 3.10+ / PyQt6 / SQLite / cryptography
> 许可证：[Apache License 2.0](LICENSE)

## 功能特性

- **空间管理**：新建 / 删除 / 重命名 / 切换，空间间完全隔离。
- **对话**：流式输出（打字机效果）、停止 / 重新生成 / 编辑消息、Token 用量统计与超限自动截断。
- **图形化记忆**：以知识图谱（节点 + 连线）展示，节点可拖拽、点击查看详情、右键复制到其他空间（记忆拼接）。超过 100 个节点自动简化。
- **对话级记忆**：每条消息可挂载独立记忆片段，可溯源到来源消息。
- **技能管理**：安装 `.skill`（zip）技能包，输入 `@技能名` 调用。
- **配置**：API Key（Fernet 加密存储）、Base URL、模型、Temperature、Top P、System Prompt，多 Key 自动轮换，修改立即生效。
- **数据**：SQLite 存储，每日自动备份，支持导出 / 导入（单空间 JSON / 整体 ZIP）。
- **系统托盘**：最小化到托盘，右键菜单显示 / 退出。
- **更新检查**：启动时检查 GitHub Releases，不强制更新。
- **快捷键**：`Ctrl+N` 空间、`Ctrl+Shift+N` 对话、`Ctrl+S` 保存、`Ctrl+F` 搜索当前、`Ctrl+Shift+F` 全局搜索、`Ctrl+,` 配置、`Esc` 停止。
- **日志**：按天切分，保留 30 天。

## 目录布局（用户数据）

所有用户数据存储在 `%USERPROFILE%\Documents\AIWorkbench\`：

```
AIWorkbench/
├── data/      数据库 (aiworkbench.db)
├── backups/   每日自动备份
├── logs/      日志（按天切分，保留 30 天）
└── skills/    技能包
```

## 快速开始（开发环境）

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行
python main.py
```

首次启动会弹出配置向导，填写 API Key、选择默认模型后进入主界面。

> 默认使用 OpenAI 兼容接口，任何兼容 `/v1/chat/completions` 的服务（DeepSeek、Kimi、通义等）都可通过修改 Base URL 接入。

## 打包

### 生成 exe（PyInstaller）

```bash
pip install pyinstaller
pyinstaller AIWorkbench.spec
# 产物为单文件 dist/AIWorkbench.exe
```

### 制作安装包（Inno Setup）

1. 下载并安装 [Inno Setup](https://jrsoftware.org/isinfo.php)。
2. 用 Inno Setup 打开并编译 `installer/AIWorkbench.iss`，生成 `AIWorkbench-Setup.exe`。

## 技能包格式（.skill）

`.skill` 是一个 zip 包，内含：

```
my-skill.skill/
├── manifest.json
└── prompt.txt
```

`manifest.json` 示例：

```json
{
  "name": "翻译官",
  "version": "1.0.0",
  "description": "中英互译助手",
  "author": "you",
  "prompt_file": "prompt.txt"
}
```

`prompt.txt` 为提示模板。启用后在输入框输入 `@翻译官 你好` 即可调用。

## 快捷键一览

| 快捷键 | 功能 |
| --- | --- |
| `Ctrl+N` | 新建空间 |
| `Ctrl+Shift+N` | 新建对话 |
| `Ctrl+S` | 保存 / 导出当前对话 |
| `Ctrl+F` | 搜索当前对话 |
| `Ctrl+Shift+F` | 全局搜索所有空间 |
| `Ctrl+,` | 打开配置面板 |
| `Enter` | 发送 |
| `Shift+Enter` | 换行 |
| `Esc` | 停止生成 |

## 贡献

欢迎提交 Issue 和 Pull Request。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[Apache License 2.0](LICENSE)