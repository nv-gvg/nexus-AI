# Nexus-AI

一个**本地优先、完全开源**的桌面 AI 工作台。你可以创建多个独立「空间（Space）」，每个空间拥有独立的对话、知识图谱记忆和配置。

> 技术栈：Python 3.10+ / PyQt6 / SQLite / cryptography
> 许可证：[Apache License 2.0](LICENSE)

## 功能特性

- **空间管理**：新建 / 删除 / 重命名 / 切换，空间间完全隔离。
- **对话**：流式输出（打字机效果）、停止 / 重新生成 / 编辑消息、Token 用量统计与超限自动截断。
- **图形化记忆**：以知识图谱（节点 + 连线）展示，节点可拖拽、点击查看详情、右键复制到其他空间（记忆拼接）。超过 100 个节点自动简化。
- **对话级记忆**：每条消息可挂载独立记忆片段，可溯源到来源消息。
- **技能管理**：安装 `.skill`（zip）技能包，输入 `@技能名` 调用。
- **MCP**：作为客户端接入外部工具（stdio / sse），也可作为 MCP 服务器把记忆开放给其它 AI。
- **配置**：API Key（Fernet 加密存储）、Base URL、模型、Temperature、Top P、System Prompt，多 Key 自动轮换，修改立即生效。
- **数据**：SQLite 存储，每日自动备份，支持导出 / 导入（单空间 JSON / 整体 ZIP）。
- **系统托盘**：最小化到托盘，右键菜单显示 / 退出。
- **更新检查**：启动时检查 GitHub Releases，不强制更新。
- **快捷键**：`Ctrl+N` 空间、`Ctrl+Shift+N` 对话、`Ctrl+S` 保存、`Ctrl+F` 搜索当前、`Ctrl+Shift+F` 全局搜索、`Ctrl+,` 配置、`Esc` 停止。
- **日志**：按天切分，保留 30 天。

## 目录布局（用户数据）

所有用户数据存储在 `%USERPROFILE%\Documents\Nexus-AI\`：

```
Nexus-AI/
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

首次启动会弹出配置向导（均可跳过），可自定义下载目录、选择是否接入 AI。

> 默认使用 OpenAI 兼容接口，任何兼容 `/v1/chat/completions` 的服务（DeepSeek、Kimi、通义等）都可通过修改 Base URL 接入。

## 打包

### 生成 exe（PyInstaller）

```bash
pip install pyinstaller
pyinstaller Nexus-AI.spec
# 产物为单文件 dist/Nexus-AI-<版本号>.exe
```

### 制作安装包（Inno Setup）

1. 下载并安装 [Inno Setup](https://jrsoftware.org/isinfo.php)。
2. 用 Inno Setup 打开并编译 `installer/Nexus-AI.iss`，生成 `Nexus-AI-Setup.exe`。

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

## MCP 支持

Nexus-AI 既是 MCP **客户端**，也是 MCP **服务器**。

### 作为客户端（接入外部工具）

在「配置面板」中添加 MCP 服务器（`stdio`：本地命令，或 `sse`：远程 URL）。对话时，AI 会把这些服务器提供的工具作为 Function Calling 能力调用，例如接入文件系统、数据库、联网搜索等工具。

### 作为服务器（开放自己的记忆）

运行：

```bash
python mcp_server.py
```

它把空间与知识图谱记忆暴露为 MCP 工具（`list_spaces` / `list_memory` / `search_memory` / `add_memory`）。在 Claude Desktop、Cursor 等客户端中把它配置为 stdio 服务器即可调用。

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

## 更新日志

### v0.2.0

**品牌升级 + 界面重构 + 启动提速**

#### 🏷 品牌升级
- 项目更名为 **Nexus-AI**（原 AIWorkbench），数据目录调整为 `%USERPROFILE%\Documents\Nexus-AI`

#### 🎨 界面重构
- **深色 / 浅色主题**：设置面板一键切换，立即生效并持久化
- **主界面精简**：顶栏快捷按钮收进菜单栏（快捷键不变），聊天区更宽
- **记忆图谱 / 技能 / 工作流**：从右侧标签页改为「查看」菜单 + 左侧导航图标独立窗口打开
- **左侧侧边栏美化**：导航按钮加大圆角，面板标题带强调色竖条，全应用统一圆角与强调色
- **聊天体验**：消息气泡按深浅色自适应，流式生成带闪烁光标

#### 🌐 外部插件市场
- 插件市场支持外部 JSON 地址（设置中可配置），后台加载，失败自动回退内置目录，离线可用

#### ⚡ 启动提速
- 打包精简：移除未使用的 `fastmcp` 及 torch / cv2 / pandas / scipy 等重库
- 产物体积 **379MB → 55.7MB**，启动时间显著缩短

#### 🚀 首次使用更友好
- 开局向导不再强制输入 API Key / 模型，可跳过稍后再配置
- 下载 / 导出目录可自定义，不再固定 C 盘

### v0.1.2

**核心更新：全新视觉设计 + MCP 生态支持**

#### 🎨 全新视觉
- **莫比乌斯环 Logo**：自适应系统主题配色（浅色→黑环，深色→白环）
- **无限符号背景**：主内容区中央渲染半透明 ∞ 符号装饰
- **深色主题**：完整的 QSS 样式表，覆盖所有控件
- **重新设计的导航栏**：品牌标识 + 快捷操作 + 状态指示

#### 🔌 MCP 生态支持
- **作为 MCP 客户端**：支持 `stdio` 和 `sse` 两种传输方式，AI 自动调用外部工具
- **作为 MCP 服务器**：开放 4 个记忆工具
  - `list_spaces` - 列出所有空间
  - `list_memory` - 获取指定空间的记忆节点
  - `search_memory` - 关键词搜索记忆
  - `add_memory` - 新增记忆条目

#### 🛠 其他改进
- 内置技能包：翻译官、代码助手、总结官 开箱即用
- Bug 修复：修复窗口缩放时的递归渲染问题
- 性能优化：背景渲染添加防抖保护

### v0.0.1

- 初始版本发布
- 空间管理、对话、知识图谱记忆、技能包等核心功能

## 贡献

欢迎提交 Issue 和 Pull Request。详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可证

[Apache License 2.0](LICENSE)