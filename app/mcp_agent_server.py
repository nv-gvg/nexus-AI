"""Nexus-AI 内置 Agent 工具集。

为 AI 提供基础干活能力（命令执行、文件读写、网页搜索等），
通过 `transport: "builtin"` 直接在进程内加载，无需独立子进程。
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Any, Callable

from .logger import get_logger


# ------------------------------------------------------------------ 工具定义
# 每个工具： (name, description, parameters_schema, callable)
ToolDef = tuple[str, str, dict[str, Any], Callable[..., str]]


def _run_command(command: str, cwd: str = "") -> str:
    """执行一条 shell 命令并返回输出。

    适合执行文件操作、git 命令、构建、启动服务等。
    """
    try:
        work_dir = cwd.strip() or None
        log = get_logger()
        log.info("Agent 执行命令: %s (cwd=%s)", command, work_dir or os.getcwd())
        result = subprocess.run(
            command,
            shell=True,
            cwd=work_dir,
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = result.stdout or ""
        err = result.stderr or ""
        if result.returncode != 0:
            return f"退出码 {result.returncode}\nSTDERR:\n{err}\nSTDOUT:\n{out}"
        if err:
            return f"STDOUT:\n{out}\nSTDERR:\n{err}"
        return out or "(命令执行成功，无输出)"
    except subprocess.TimeoutExpired:
        return "错误：命令执行超时（120 秒）"
    except Exception as exc:  # noqa: BLE001
        return f"执行失败: {exc}"


def _read_file(path: str) -> str:
    """读取一个文本文件的内容。

    适合查看代码、配置文件、日志等。
    """
    try:
        p = Path(path)
        if not p.exists():
            return f"错误：文件不存在 ({path})"
        if not p.is_file():
            return f"错误：路径不是一个文件 ({path})"
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.count("\n") + 1
        return f"文件 {path} ({lines} 行):\n\n{content[:50000]}"
    except Exception as exc:  # noqa: BLE001
        return f"读取失败: {exc}"


def _write_file(path: str, content: str) -> str:
    """写入一个文本文件。如果文件不存在则创建，存在则覆盖。"""
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"已写入 {path} ({len(content)} 字符)"
    except Exception as exc:  # noqa: BLE001
        return f"写入失败: {exc}"


def _list_files(path: str = ".", pattern: str = "") -> str:
    """列出指定目录下的文件和子目录。可指定 glob 模式过滤。"""
    try:
        p = Path(path)
        if not p.exists():
            return f"错误：目录不存在 ({path})"
        if not p.is_dir():
            return f"错误：路径不是目录 ({path})"

        if pattern:
            items = list(p.glob(pattern))
        else:
            items = list(p.iterdir())

        if not items:
            return f"({path} 下没有匹配的文件或目录)"

        lines = []
        dirs = sorted([x for x in items if x.is_dir()])
        files = sorted([x for x in items if x.is_file()])

        if dirs:
            lines.append("目录:")
            for d in dirs:
                lines.append(f"  📁 {d.name}/")
        if files:
            lines.append("文件:")
            for f in files:
                size = f.stat().st_size
                size_str = f"{size:,} B" if size < 1024 else f"{size/1024:.1f} KB"
                lines.append(f"  📄 {f.name}  ({size_str})")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        return f"列出失败: {exc}"


def _glob_files(pattern: str, path: str = ".") -> str:
    """按 glob 模式搜索文件（支持 ** 递归匹配）。返回匹配的文件路径列表。"""
    try:
        root = Path(path)
        if not root.exists():
            return f"错误：路径不存在 ({path})"
        matches = list(root.rglob(pattern)) if "**" in pattern else list(root.glob(pattern))
        if not matches:
            return f"在 {path} 下未找到匹配 {pattern} 的文件"
        result = "\n".join(str(m) for m in sorted(matches)[:200])
        if len(matches) > 200:
            result += f"\n... (共 {len(matches)} 个，仅显示前 200 个)"
        return result
    except Exception as exc:  # noqa: BLE001
        return f"搜索失败: {exc}"


def _grep_text(pattern: str, path: str = ".") -> str:
    """在文件的文本内容中搜索匹配的行。支持正则表达式。"""
    try:
        root = Path(path)
        if not root.exists():
            return f"错误：路径不存在 ({path})"

        import re

        regex = re.compile(pattern, re.IGNORECASE)
        matches: list[str] = []

        for p in root.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in (".exe", ".dll", ".pyc", ".ico", ".png", ".jpg", ".db", ".zip"):
                continue
            try:
                for lineno, line in enumerate(p.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                    if regex.search(line):
                        # 限长显示
                        line_stripped = line.strip()[:120]
                        matches.append(f"{p}:{lineno}: {line_stripped}")
                        if len(matches) >= 100:
                            break
            except (OSError, UnicodeDecodeError):
                continue
            if len(matches) >= 100:
                matches.append("(达到 100 条上限，截断)")
                break

        if not matches:
            return f"在 {root} 下未找到匹配「{pattern}」的行"
        return "\n".join(matches)
    except Exception as exc:  # noqa: BLE001
        return f"搜索失败: {exc}"


def _get_system_info() -> str:
    """获取当前系统信息（操作系统、工作目录、Python 版本等）。"""
    info = {
        "OS": os.name,
        "系统": sys.platform,
        "工作目录": os.getcwd(),
        "Python 版本": sys.version.split()[0],
        "Python 路径": sys.executable,
    }
    return json.dumps(info, ensure_ascii=False, indent=2)


def _ask_user(question: str) -> str:
    """向用户提问并等待回答。当你需要用户做决定、提供信息或确认时使用。

    注意：这是一个阻塞操作，不要在可以自行判断的情况下使用。
    """
    log = get_logger()
    log.warning("Agent 要求用户输入: %s", question)
    # 在纯终端环境中，直接读取 stdin
    try:
        print(f"\n[Agent 需要你的输入] {question}")
        print("> ", end="", flush=True)
        answer = sys.stdin.readline().strip()
        return f"用户回答: {answer}"
    except Exception as exc:  # noqa: BLE001
        return f"获取用户输入失败: {exc}"


def _web_search(query: str) -> str:
    """搜索互联网，返回搜索结果摘要。"""
    try:
        import urllib.parse
        import urllib.request
        import urllib.error

        log = get_logger()
        log.info("Agent 搜索: %s", query)

        # 使用 DuckDuckGo 的 lite 接口（无需 API Key）
        url = "https://lite.duckduckgo.com/lite/"
        data = urllib.parse.urlencode({"q": query}).encode()
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # 简单解析出结果文本
        results: list[str] = []
        in_result = False
        for line in html.splitlines():
            stripped = line.strip()
            if '<a rel="nofollow" href="' in stripped:
                # 提取链接和标题
                href_start = stripped.find('href="') + 6
                href_end = stripped.find('"', href_start)
                href = stripped[href_start:href_end]
                # 提取标题
                title = stripped[stripped.find(">", href_end) + 1 : stripped.find("</a>")]
                results.append(f"{title}\n  {href}")
            elif stripped and not stripped.startswith("<") and not stripped.startswith("  "):
                if results and results[-1].endswith("\n  " + href):
                    continue

        if not results:
            # 尝试从 JSON 接口获取
            return _web_search_fallback(query)

        return "\n\n".join(results[:10])
    except Exception as exc:  # noqa: BLE001
        return _web_search_fallback(query)


def _web_search_fallback(query: str) -> str:
    """备用搜索：使用 DuckDuckGo 的非官方 API。"""
    try:
        import urllib.parse
        import urllib.request
        import json

        url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        if data.get("AbstractText"):
            results.append(f"摘要: {data['AbstractText']}")
        if data.get("AbstractURL"):
            results.append(f"来源: {data['AbstractURL']}")
        for topic in data.get("RelatedTopics", []):
            if "Text" in topic:
                results.append(topic["Text"])
        return "\n\n".join(results[:10]) if results else "（无搜索结果）"
    except Exception:  # noqa: BLE001
        return "（搜索失败，无法访问网络或搜索引擎）"


def _web_fetch(url: str) -> str:
    """获取一个网页的内容，返回纯文本格式。"""
    try:
        import urllib.request

        log = get_logger()
        log.info("Agent 获取网页: %s", url)

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode("utf-8", errors="replace")

        # 简单清理 HTML 标签
        import re

        text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        text = textwrap.shorten(text, width=30000, placeholder="... (截断)")
        return text
    except Exception as exc:  # noqa: BLE001
        return f"获取网页失败: {exc}"


# ------------------------------------------------------------------ 工具注册表
TOOLS: list[ToolDef] = [
    (
        "run_command",
        "执行一条 shell 命令（支持管道、重定向、链式操作）。"
        "适合执行文件操作、git 命令、构建、启动服务等。"
        "注意：cwd 是可选参数，不传则使用工作目录。",
        {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的命令"},
                "cwd": {
                    "type": "string",
                    "description": "可选，工作目录（绝对路径），不传则使用当前工作目录",
                },
            },
            "required": ["command"],
        },
        _run_command,
    ),
    (
        "read_file",
        "读取一个文本文件的内容。适合查看代码、配置文件、日志等。",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件的绝对路径"}
            },
            "required": ["path"],
        },
        _read_file,
    ),
    (
        "write_file",
        "写入一个文本文件。如果文件不存在则创建，存在则覆盖。注意：会覆盖已有内容！",
        {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件的绝对路径"},
                "content": {"type": "string", "description": "要写入的文本内容"},
            },
            "required": ["path", "content"],
        },
        _write_file,
    ),
    (
        "list_files",
        "列出指定目录下的文件和子目录。可指定 glob 模式过滤文件名。",
        {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "可选，目录路径，默认为当前工作目录",
                    "default": ".",
                },
                "pattern": {
                    "type": "string",
                    "description": "可选，glob 模式过滤（如 *.py），不传则列出全部",
                },
            },
            "required": [],
        },
        _list_files,
    ),
    (
        "glob_files",
        "按 glob 模式搜索文件（支持 ** 递归匹配）。如 **/*.py 搜索所有 Python 文件。",
        {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "glob 模式，如 **/*.py"},
                "path": {
                    "type": "string",
                    "description": "可选，搜索根目录，默认为当前目录",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
        _glob_files,
    ),
    (
        "grep_text",
        "在文件的文本内容中搜索匹配的行。支持正则表达式。适合搜索日志、代码中的关键词。",
        {
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "description": "搜索模式（支持正则）"},
                "path": {
                    "type": "string",
                    "description": "可选，搜索根目录，默认为当前目录",
                    "default": ".",
                },
            },
            "required": ["pattern"],
        },
        _grep_text,
    ),
    (
        "get_system_info",
        "获取当前系统信息（操作系统、工作目录、Python 版本等）。",
        {"type": "object", "properties": {}, "required": []},
        _get_system_info,
    ),
    (
        "ask_user",
        "向用户提问并等待回答。当你需要用户做决定、提供信息或确认时使用。"
        "注意：仅在无法自行判断时使用。",
        {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "要向用户提的问题"}
            },
            "required": ["question"],
        },
        _ask_user,
    ),
    (
        "web_search",
        "搜索互联网，返回搜索结果摘要。适合查找最新信息、文档、新闻等。",
        {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "搜索关键词"}
            },
            "required": ["query"],
        },
        _web_search,
    ),
    (
        "web_fetch",
        "获取一个网页的内容，返回纯文本格式。适合阅读文档、文章等。",
        {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "网页完整 URL"}
            },
            "required": ["url"],
        },
        _web_fetch,
    ),
]


def get_tools() -> list[ToolDef]:
    """返回所有注册的工具列表。"""
    return list(TOOLS)