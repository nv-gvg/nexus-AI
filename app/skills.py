"""技能管理。

技能包格式 .skill（zip），包含:
    manifest.json   描述技能
    prompt.txt      提示模板

输入框中输入 @技能名 时，会自动把技能的提示模板注入到系统提示中。
"""

from __future__ import annotations

import json
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import paths
from .logger import get_logger


@dataclass
class Skill:
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    prompt: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "prompt": self.prompt,
        }


class SkillManager:
    def __init__(self) -> None:
        self.root = paths.skills_dir()
        self.root.mkdir(parents=True, exist_ok=True)
        self.log = get_logger()

    def install(self, zip_path: str | Path) -> Skill:
        """安装 .skill 压缩包。"""
        zip_path = Path(zip_path)
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = zf.namelist()
            if "manifest.json" not in names:
                raise ValueError("技能包缺少 manifest.json")

            manifest = json.loads(zf.read("manifest.json").decode("utf-8"))
            name = manifest.get("name")
            if not name:
                raise ValueError("manifest.json 缺少 name 字段")

            prompt_file = manifest.get("prompt_file", "prompt.txt")
            prompt = ""
            if prompt_file in names:
                prompt = zf.read(prompt_file).decode("utf-8")
            else:
                prompt = manifest.get("prompt", "")

            target_dir = self.root / name
            target_dir.mkdir(parents=True, exist_ok=True)
            zf.extractall(target_dir)

        skill = Skill(
            name=name,
            version=manifest.get("version", "1.0.0"),
            description=manifest.get("description", ""),
            author=manifest.get("author", ""),
            prompt=prompt,
        )
        self.log.info("安装技能包: %s", name)
        return skill

    def list_skills(self) -> list[Skill]:
        """枚举所有已安装技能。"""
        skills: list[Skill] = []
        if not self.root.exists():
            return skills
        for d in sorted(self.root.iterdir()):
            if not d.is_dir():
                continue
            manifest_path = d / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                prompt_file = manifest.get("prompt_file", "prompt.txt")
                prompt = ""
                pf = d / prompt_file
                if pf.exists():
                    prompt = pf.read_text(encoding="utf-8")
                skills.append(
                    Skill(
                        name=manifest.get("name", d.name),
                        version=manifest.get("version", "1.0.0"),
                        description=manifest.get("description", ""),
                        author=manifest.get("author", ""),
                        prompt=prompt,
                    )
                )
            except (json.JSONDecodeError, OSError) as exc:
                self.log.warning("加载技能失败 %s: %s", d, exc)
        return skills

    def get(self, name: str) -> Skill | None:
        for s in self.list_skills():
            if s.name == name:
                return s
        return None

    def uninstall(self, name: str) -> None:
        import shutil

        target = self.root / name
        if target.exists():
            shutil.rmtree(target)
            self.log.info("卸载技能包: %s", name)

    def resolve_mentions(self, text: str, enabled: set[str]) -> tuple[str, str]:
        """解析输入中的 @技能名，返回 (清洗后的文本, 注入的提示)。"""
        import re

        injected: list[str] = []
        cleaned_parts: list[str] = []
        for token in text.split():
            m = re.fullmatch(r"@([\w\-]+)", token)
            if m and m.group(1) in enabled:
                skill = self.get(m.group(1))
                if skill:
                    injected.append(f"[技能: {skill.name}] {skill.prompt}")
                    continue
            cleaned_parts.append(token)
        return " ".join(cleaned_parts), "\n".join(injected)