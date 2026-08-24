"""MCP 客户端：连接外部 MCP 服务器，把工具转为 OpenAI Function Calling 格式并执行。

支持两种传输：
- stdio：本地启动一个命令作为 MCP 服务器（本地优先）
- sse/http：连接远程 MCP 服务器 URL

所有 mcp 相关导入均为延迟加载，未安装 mcp 库时不影响程序其它功能。
"""

from __future__ import annotations

import asyncio
from typing import Any

from .logger import get_logger


def _run_async(coro: Any) -> Any:
    """在同步线程中运行一个协程（PyQt 后台线程无事件循环）。"""
    try:
        return asyncio.run(coro)
    except RuntimeError:
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()


class MCPError(Exception):
    """MCP 相关错误。"""


def _extract_text(result: Any) -> str:
    """从 call_tool 结果中提取文本内容。"""
    parts: list[str] = []
    for item in getattr(result, "content", []):
        if getattr(item, "type", "") == "text":
            parts.append(item.text)
        else:
            parts.append(str(item))
    return "\n".join(parts) if parts else "(无文本输出)"


class MCPClient:
    """同步封装的多 MCP 服务器客户端。

    支持三种传输方式：
    - stdio：本地启动一个子进程作为 MCP 服务器
    - sse/http：连接远程 MCP 服务器 URL
    - builtin：在进程内直接加载工具模块（无需子进程，最可靠）
    """

    def __init__(self, servers: list[dict[str, Any]]) -> None:
        self.servers = [s for s in servers if s.get("enabled", True)]
        self.log = get_logger()
        self._tool_to_server: dict[str, int] = {}
        self._builtin_tools: dict[str, dict[str, Any]] = {}  # name -> {fn, etc}

    @property
    def enabled(self) -> bool:
        return bool(self.servers)

    def list_tools(self) -> list[dict[str, Any]]:
        """返回 OpenAI tools 格式的工具列表（失败服务器自动跳过）。"""
        tools: list[dict[str, Any]] = []
        self._tool_to_server = {}
        self._builtin_tools = {}
        for idx, server in enumerate(self.servers):
            transport = self._transport(server)
            if transport == "builtin":
                try:
                    bt = self._list_builtin_tools()
                except Exception as exc:  # noqa: BLE001
                    self.log.warning("内置 Agent 工具加载失败: %s", exc)
                    continue
                for t in bt:
                    tools.append(t["openai_tool"])
                    self._tool_to_server[t["name"]] = idx
                    self._builtin_tools[t["name"]] = t
                continue
            try:
                raw_tools = _run_async(self._list_tools_for(server))
            except Exception as exc:  # noqa: BLE001
                self.log.warning("MCP 服务器 %s 连接失败: %s", server.get("name", "?"), exc)
                continue
            for t in raw_tools:
                tools.append(self._to_openai_tool(t))
                self._tool_to_server[t.name] = idx
        return tools

    def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        idx = self._tool_to_server.get(tool_name)
        if idx is None:
            raise MCPError(f"工具 {tool_name} 不可用：对应 MCP 服务器未连接")
        server = self.servers[idx]
        transport = self._transport(server)
        if transport == "builtin":
            return self._call_builtin_tool(tool_name, arguments)
        return _run_async(self._call_tool_on_server(server, tool_name, arguments))

    # ------------------------------------------------------------------ 转换
    @staticmethod
    def _to_openai_tool(tool: Any) -> dict[str, Any]:
        schema = getattr(tool, "inputSchema", None) or {"type": "object", "properties": {}}
        return {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": getattr(tool, "description", "") or "",
                "parameters": schema,
            },
        }

    # ------------------------------------------------------------------ 分发
    @staticmethod
    def _transport(server: dict[str, Any]) -> str:
        return (server.get("transport") or "stdio").lower()

    async def _list_tools_for(self, server: dict[str, Any]) -> list[Any]:
        if self._transport(server) in ("sse", "http"):
            return await self._sse_list(server.get("url", ""))
        return await self._stdio_list(server.get("command", ""), server.get("args", []))

    async def _call_tool_on_server(
        self, server: dict[str, Any], tool_name: str, arguments: dict[str, Any]
    ) -> str:
        if self._transport(server) in ("sse", "http"):
            return await self._sse_call(server.get("url", ""), tool_name, arguments)
        return await self._stdio_call(
            server.get("command", ""), server.get("args", []), tool_name, arguments
        )

    # ------------------------------------------------------------------ stdio
    @staticmethod
    async def _stdio_list(command: str, args: list[str]) -> list[Any]:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=command, args=list(args or []))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return list(result.tools)

    @staticmethod
    async def _stdio_call(
        command: str, args: list[str], tool_name: str, arguments: dict[str, Any]
    ) -> str:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        params = StdioServerParameters(command=command, args=list(args or []))
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return _extract_text(result)

    # ------------------------------------------------------------------ sse/http
    @staticmethod
    async def _sse_list(url: str) -> list[Any]:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return list(result.tools)

    @staticmethod
    async def _sse_call(url: str, tool_name: str, arguments: dict[str, Any]) -> str:
        from mcp import ClientSession
        from mcp.client.sse import sse_client

        async with sse_client(url) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(tool_name, arguments=arguments)
                return _extract_text(result)

    # ------------------------------------------------------------------ builtin（进程内加载工具，无需子进程）
    def _list_builtin_tools(self) -> list[dict[str, Any]]:
        """从 app.mcp_agent_server 模块加载内置工具。"""
        from . import mcp_agent_server

        result: list[dict[str, Any]] = []
        for name, desc, params, _fn in mcp_agent_server.get_tools():
            result.append(
                {
                    "name": name,
                    "openai_tool": {
                        "type": "function",
                        "function": {
                            "name": name,
                            "description": desc,
                            "parameters": params,
                        },
                    },
                }
            )
        return result

    def _call_builtin_tool(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """在进程内直接调用内置工具函数。"""
        from . import mcp_agent_server

        for name, _desc, _params, fn in mcp_agent_server.get_tools():
            if name == tool_name:
                return fn(**arguments)
        raise MCPError(f"内置工具 {tool_name} 未找到")