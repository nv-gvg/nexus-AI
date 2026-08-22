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


# ------------------------------------------------------------------ 内置技能
BUILTIN_SKILLS: list[dict[str, Any]] = [
    {
        "name": "翻译官",
        "version": "1.0.0",
        "description": "中英互译助手",
        "author": "Nexus-AI",
        "prompt": "你是一名专业翻译。用户输入中文就翻译成英文，输入英文就翻译成中文。只输出译文，不要额外解释。",
    },
    {
        "name": "代码助手",
        "version": "1.0.0",
        "description": "编写、解释、调试代码",
        "author": "Nexus-AI",
        "prompt": "你是一名资深程序员。帮用户编写、解释和调试代码，给出可直接运行的代码并简要说明关键思路，优先使用用户指定的语言。",
    },
    {
        "name": "总结官",
        "version": "1.0.0",
        "description": "把长文本提炼成要点",
        "author": "Nexus-AI",
        "prompt": "你是一名总结专家。把用户提供的长文本提炼成简洁、条理清晰的要点，可用列表或分点呈现，保留关键信息、删除冗余。",
    },
]


def _write_skill(target: Path, spec: dict[str, Any]) -> None:
    """把内置技能写成 skills 目录下独立的技能包文件夹。"""
    target.mkdir(parents=True, exist_ok=True)
    manifest = {
        "name": spec["name"],
        "version": spec.get("version", "1.0.0"),
        "description": spec.get("description", ""),
        "author": spec.get("author", ""),
        "prompt_file": "prompt.txt",
    }
    (target / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (target / "prompt.txt").write_text(spec.get("prompt", ""), encoding="utf-8")


# ------------------------------------------------------------------ 插件市场
# 精选可一键安装的插件包（本应用内置插件市场，离线可用）。
# 若环境联网，下拉脚本会尝试从远程 GitHub 目录合并更新；失败则使用本地目录。
MARKET_PLUGINS: list[dict[str, Any]] = [
    {
        "name": "写作润色",
        "version": "1.0.0",
        "description": "把写得一般的文字改成流畅、优雅的表达",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名资深文字编辑。请对用户输入进行润色：修正语病、搭配、标点，让表达更流畅自然，保持原意，不改变结构和长度，只输出改写后的文本。",
    },
    {
        "name": "英语老师",
        "version": "1.0.0",
        "description": "讲解英语语法、搭配并给出例句练习",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名温柔的英语老师。针对用户的问题用中文讲解，必要时给英文例句和针对性小练习，语言生动易懂。",
    },
    {
        "name": "数学解题",
        "version": "1.0.0",
        "description": "分步讲解数学题并给出解题思路",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名数学老师。请把题目分步讲解清楚，写出解题思路和公式，最后给出答案，并用通俗语言解释每一步。",
    },
    {
        "name": "演讲稿助手",
        "version": "1.0.0",
        "description": "根据主题生成有感染力、结构清晰的演讲稿",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名演讲教练。请根据用户给出的主题和场合，写一篇结构清晰、有感染力、口语化的演讲稿，包含开场、主体和结尾，并标出停顿点。",
    },
    {
        "name": "代码解释器",
        "version": "1.0.0",
        "description": "逐行解释代码并说明运行逻辑",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名耐心讲解的老师。请逐段解释用户给出的代码：先概括整体作用，再解释每一部分的功能和语法，最后指出潜在问题。",
    },
    {
        "name": "学习计划师",
        "version": "1.0.0",
        "description": "根据目标制定可执行的每日学习计划",
        "author": "Nexus-AI 插件市场",
        "prompt": "你是一名学习规划师。请根据用户的目标、每天可投入时间和水平，制定一份具体、可执行、有复习节奏的学习计划，按天/S 安排，并给出里程碑。",
    },
]


def market_catalog(remote: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """返回插件市场可安装的插件目录。

    若传入可用的远程目录则优先返回远程目录（附加标记 source="remote"），
    否则回退到本地内置目录，保证离线可用。
    """
    if remote:
        result = []
        for spec in remote:
            item = dict(spec)
            item.setdefault("source", "remote")
            result.append(item)
        return result
    return [dict(spec) for spec in MARKET_PLUGINS]


def fetch_remote_market(url: str, timeout: float = 8.0) -> list[dict[str, Any]] | None:
    """从外部市场 URL 拉取插件目录（JSON 数组），失败返回 None。

    每项需含 name/version/description/prompt（author 可选）。
    """
    if not url or not url.strip():
        return None
    import urllib.request

    try:
        req = urllib.request.Request(
            url.strip(),
            headers={"User-Agent": "Nexus-AI/0.2.0"},
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            payload = json.loads(resp.read().decode("utf-8"))
        if not isinstance(payload, list):
            return None
        specs = []
        for item in payload:
            if not isinstance(item, dict) or not item.get("name"):
                continue
            item.setdefault("version", "1.0.0")
            item.setdefault("description", "")
            item.setdefault("author", "外部插件市场")
            item.setdefault("prompt", "")
            specs.append(item)
        return specs or None
    except Exception:  # noqa: BLE001
        return None


def install_market_plugin(spec: dict[str, Any], enable: bool = True) -> None:
    """把插件市场中的一项写成本地技能包，并按需启用。"""
    from .config import get_config

    name = spec.get("name", "")
    if not name:
        raise ValueError("插件缺少名称")
    target = paths.skills_dir() / name
    _write_skill(target, spec)
    if enable:
        get_config().enable_skill(name)
    get_logger().info("已安装插件市场技能: %s", name)


def install_builtin_skills(config=None) -> list[str]:
    """首次运行时安装内置技能；仅对「新安装」的技能执行启用。"""
    from .config import get_config

    installed: list[str] = []
    cfg = config if config is not None else get_config()
    for spec in BUILTIN_SKILLS:
        name = spec["name"]
        target = paths.skills_dir() / name
        if not (target / "manifest.json").exists():
            _write_skill(target, spec)
            installed.append(name)
            cfg.enable_skill(name)
    if installed:
        get_logger().info("已安装内置技能: %s", ", ".join(installed))
    return installed