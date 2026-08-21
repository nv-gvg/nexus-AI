"""OpenAI 兼容 API 客户端。

- 支持流式输出（SSE）。
- 多 API Key 轮换：遇到 401/429/5xx 自动切换下一个 Key。
- Token 估算与上下文截断（保留 System Prompt + 最近 N 条）。
"""

from __future__ import annotations

import json
from typing import Any, Callable

import requests

from .config import get_config
from .logger import get_logger

# 限制单次请求体约 K 个 token 所对应的字符上限（粗略按 1 token ≈ 4 字符）
MAX_CONTEXT_CHARS = 32_000
KEEP_RECENT_MESSAGES = 20


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：中文约 1 字 1 token，英文约 4 字符 1 token。"""
    if not text:
        return 0
    cjk = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    other = len(text) - cjk
    return cjk + (other // 4) + 1


def truncate_history(
    messages: list[dict[str, str]],
    system_prompt: str,
    max_chars: int = MAX_CONTEXT_CHARS,
    keep_recent: int = KEEP_RECENT_MESSAGES,
) -> list[dict[str, str]]:
    """保留 System Prompt + 最近 N 条消息，并控制总长度。"""
    result: list[dict[str, str]] = []
    total = len(system_prompt)
    if system_prompt:
        result.append({"role": "system", "content": system_prompt})

    recent = messages[-(keep_recent):]
    # 从最近的开始向前填充，直到接近上限
    to_add: list[dict[str, str]] = []
    for msg in reversed(recent):
        size = len(msg.get("content", ""))
        if total + size > max_chars and to_add:
            break
        to_add.append(msg)
        total += size
    to_add.reverse()
    result.extend(to_add)
    return result


class APIError(Exception):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIClient:
    def __init__(self) -> None:
        self.config = get_config()
        self.log = get_logger()

    def _headers(self, api_key: str) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }

    def _resolve_skill_mentions(self, text: str) -> str:
        """将 @技能名 替换为技能提示模板（由调用方注入，这里只保留原样）。"""
        return text

    def build_payload(self, messages: list[dict[str, str]], system_extra: str = "") -> dict[str, Any]:
        system_prompt = self.config.get("system_prompt", "")
        if system_extra:
            system_prompt = f"{system_prompt}\n\n{system_extra}"
        history = truncate_history(messages, system_prompt)
        return {
            "model": self.config.get("model", "gpt-4o-mini"),
            "messages": history,
            "temperature": float(self.config.get("temperature", 0.7)),
            "top_p": float(self.config.get("top_p", 1.0)),
            "stream": True,
        }

    def _url(self) -> str:
        base = self.config.get("base_url", "https://api.openai.com/v1").rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    def stream_chat(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], None],
        should_stop: Callable[[], bool],
        system_extra: str = "",
    ) -> str:
        """同步阻塞执行流式请求，返回完整回复文本。"""
        return self._stream_with_retry(messages, on_token, should_stop, system_extra)

    def _stream_with_retry(
        self,
        messages: list[dict[str, str]],
        on_token: Callable[[str], None],
        should_stop: Callable[[], bool],
        system_extra: str,
    ) -> str:
        keys = self.config.get_api_keys()
        if not keys:
            raise APIError("未配置 API Key，请先在配置面板中设置。")

        payload = self.build_payload(messages, system_extra)
        last_err: APIError | None = None

        # 最多尝试 len(keys) 次，每次轮换 Key
        for _ in range(len(keys)):
            api_key = self.config.next_api_key()
            if not api_key:
                break
            try:
                return self._do_stream(api_key, payload, on_token, should_stop)
            except APIError as exc:
                last_err = exc
                self.log.warning("Key 请求失败(状态码 %s)，切换到下一个 Key", exc.status_code)
                # 不可重试的错误不再切换
                if exc.status_code in (400, 401, 403):
                    raise exc
                continue
        raise last_err or APIError("所有 API Key 均已失败")

    def _do_stream(
        self,
        api_key: str,
        payload: dict[str, Any],
        on_token: Callable[[str], None],
        should_stop: Callable[[], bool],
    ) -> str:
        url = self._url()
        try:
            resp = requests.post(
                url,
                headers=self._headers(api_key),
                json=payload,
                stream=True,
                timeout=(10, 300),
            )
        except requests.RequestException as exc:
            raise APIError(f"网络请求失败: {exc}") from exc

        if resp.status_code != 200:
            detail = resp.text[:500]
            raise APIError(f"API 返回错误 {resp.status_code}: {detail}", resp.status_code)

        full_text: list[str] = []
        try:
            for line in resp.iter_lines(decode_unicode=True):
                if should_stop():
                    break
                if not line or not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                except json.JSONDecodeError:
                    continue
                delta = (
                    obj.get("choices", [{}])[0]
                    .get("delta", {})
                    .get("content")
                )
                if delta:
                    full_text.append(delta)
                    on_token(delta)
        finally:
            resp.close()
        return "".join(full_text)