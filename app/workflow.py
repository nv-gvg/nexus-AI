"""工作流管理。

工作流由多个「步骤（step）」串联，每个步骤是一个提示词（可引用上一步输出）。
工作流以 JSON 文件存储于数据根目录的 workflows 目录下，可在工作流面板中
创建、编辑、删除与运行。
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from . import paths
from .logger import get_logger


@dataclass
class WorkflowStep:
    name: str
    prompt: str
    use_previous: bool = True  # 是否把上一步输出追加到本步的输入

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "prompt": self.prompt, "use_previous": self.use_previous}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorkflowStep":
        return cls(
            name=data.get("name", "步骤"),
            prompt=data.get("prompt", ""),
            use_previous=bool(data.get("use_previous", True)),
        )


@dataclass
class Workflow:
    id: str
    name: str
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    created_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Workflow":
        return cls(
            id=data.get("id", ""),
            name=data.get("name", "未命名工作流"),
            description=data.get("description", ""),
            steps=[WorkflowStep.from_dict(s) for s in data.get("steps", [])],
            created_at=data.get("created_at", ""),
        )


class WorkflowManager:
    def __init__(self) -> None:
        self.root = paths.workflows_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = get_logger()
        self._lock = threading.Lock()

    def _path(self, workflow_id: str) -> Path:
        return self.root / f"{workflow_id}.json"

    def list_workflows(self) -> list[Workflow]:
        items: list[Workflow] = []
        if not self.root.exists():
            return items
        for f in sorted(self.root.glob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                items.append(Workflow.from_dict(data))
            except (json.JSONDecodeError, OSError) as exc:
                self.log.warning("加载工作流失败 %s: %s", f, exc)
        return items

    def get(self, workflow_id: str) -> Workflow | None:
        p = self._path(workflow_id)
        if not p.exists():
            return None
        try:
            return Workflow.from_dict(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            return None

    def save(self, workflow: Workflow) -> None:
        with self._lock:
            self.root.mkdir(parents=True, exist_ok=True)
            self._path(workflow.id).write_text(
                json.dumps(workflow.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
            )
            self.log.info("已保存工作流: %s", workflow.name)

    def delete(self, workflow_id: str) -> None:
        p = self._path(workflow_id)
        if p.exists():
            p.unlink()
            self.log.info("已删除工作流: %s", workflow_id)


def suggest_workflow_presets() -> list[Workflow]:
    """内置几个示例工作流，便于用户快速上手。"""
    return [
        Workflow(
            id="preset_summary",
            name="中文摘要工程",
            description="把输入打磨成结构化的中文要点摘要",
            steps=[
                WorkflowStep("提炼要点", "把下面的内容提炼成 5-8 条要点，用短句呈现：\n{INPUT}"),
                WorkflowStep("重写润色", "把上一步的要点改写得更准确、精炼、通顺：\n{INPUT}"),
            ],
            created_at="",
        ),
        Workflow(
            id="preset_review",
            name="代码审查流程",
            description="对输入的代码进行问题扫描并给出修复建议",
            steps=[
                WorkflowStep("静态扫描", "审查以下代码，列出可读性、安全和性能问题：\n{INPUT}"),
                WorkflowStep("给出建议", "针对上一步的问题给出具体、可落地的修复建议：\n{INPUT}"),
            ],
            created_at="",
        ),
    ]