"""知识库元数据加载器 — 扫描 知识库/ 和 skills/ 目录，
读取 SKILL.md 的 YAML frontmatter 和 workflow.json，
将 triggers、工作流、能力描述注入运行时。"""

import json
import logging
import os
import re
import yaml

logger = logging.getLogger("app.knowledge_loader")

# 需要扫描的目录列表（相对于项目根目录）
from pathlib import Path as _Path
_PROJECT_DIR = _Path(__file__).resolve().parent.parent.parent
SCAN_DIRS = [str(_PROJECT_DIR / "知识库"), str(_PROJECT_DIR / "skills")]

# 内部 Skills（不对用户暴露，仅用于 agent 自身能力）
INTERNAL_SKILLS = {"find-skills", "self-improvement", "planning-with-files-zh"}

_skill_cache: dict = {}
_loaded = False


def load_skills() -> dict:
    """扫描所有目录，提取 SKILL.md 和 workflow.json。"""
    global _skill_cache, _loaded
    if _loaded:
        return _skill_cache

    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            logger.info("目录 %s 不存在，跳过", scan_dir)
            continue

        for root, dirs, files in os.walk(scan_dir):
            for fname in files:
                filepath = os.path.join(root, fname)
                if fname == "SKILL.md":
                    _load_skill_md(filepath)
                elif fname == "workflow.json":
                    _load_workflow_json(filepath)

    _loaded = True
    user_count = len(get_user_skills())
    logger.info("知识库元数据加载完成: %d 个 skill（%d 个面向用户）",
                len(_skill_cache), user_count)
    return _skill_cache


def _load_skill_md(filepath: str):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        frontmatter = _parse_yaml_frontmatter(content)
        if not frontmatter:
            return

        name = frontmatter.get("name", os.path.basename(os.path.dirname(filepath)))

        # 提取 triggers：优先用 frontmatter 中的 triggers 字段，
        # 其次从 description 中提取中文触发词，
        # 最后从正文"何时使用"章节提取
        triggers = _extract_triggers(frontmatter, content, name)

        skill_dir = os.path.dirname(filepath)
        workflow = _load_workflow_in_dir(skill_dir)
        is_internal = name in INTERNAL_SKILLS
        user_invocable = frontmatter.get("user-invocable", not is_internal)

        _skill_cache[name] = {
            "name": name,
            "description": frontmatter.get("description", ""),
            "category": frontmatter.get("category", ""),
            "triggers": triggers,
            "directory": skill_dir,
            "workflow": workflow,
            "is_internal": is_internal,
            "user_invocable": user_invocable,
        }
        logger.info("加载 Skill: %s (triggers: %s, user:%s)",
                    name, triggers, user_invocable)
    except Exception:
        logger.warning("解析 SKILL.md 失败: %s", filepath, exc_info=True)


def _extract_triggers(frontmatter: dict, content: str, skill_name: str) -> list:
    """从多个来源提取触发关键词。"""
    triggers = []

    # 1. 从 frontmatter 的 triggers 字段
    raw = frontmatter.get("triggers", "")
    if isinstance(raw, str) and raw.strip():
        triggers.extend([t.strip() for t in raw.split(",") if t.strip()])

    # 2. 从 description 中提取中文触发词（如 planning-with-files-zh 的格式）
    if not triggers:
        desc = frontmatter.get("description", "")
        triggers_from_desc = _parse_chinese_triggers(desc)
        triggers.extend(triggers_from_desc)

    # 3. 从正文的"何时使用/触发条件"章节提取
    if not triggers:
        triggers_from_body = _parse_triggers_from_body(content, skill_name)
        triggers.extend(triggers_from_body)

    return triggers


def _parse_chinese_triggers(text: str) -> list:
    """从文本中提取顿号/逗号分隔的中文触发词。"""
    trig_match = re.search(r"触发词[：:](.+)", text)
    if trig_match:
        segment = trig_match.group(1).strip()
        return [t.strip() for t in re.split(r"[、，,]", segment) if t.strip() and len(t.strip()) >= 2]
    return []


def _parse_triggers_from_body(content: str, skill_name: str) -> list:
    """从 SKILL.md 正文的'何时使用'章节解析触发短语。"""
    triggers = []

    if skill_name == "baidu-map-api":
        # 地图相关触发词
        triggers = [
            "附近医院", "找医院", "搜索医院", "医院在哪里",
            "怎么去", "路线", "导航", "地图",
        ]

    # 匹配 "何时使用" 或 "触发条件" 章节中的引号内容
    section_match = re.search(
        r"(?:何时使用|触发条件|When to Use).*?\n(.*?)(?=\n##|\n#|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if section_match:
        section = section_match.group(1)
        quoted = re.findall(r"[「「](.+?)[」」]", section)
        triggers.extend([q.strip() for q in quoted if len(q.strip()) >= 2])

    return triggers


def _load_workflow_in_dir(dirpath: str) -> list | None:
    wf_path = os.path.join(dirpath, "workflow.json")
    if not os.path.isfile(wf_path):
        return None
    return _load_workflow_json(wf_path)


def _load_workflow_json(filepath: str) -> list | None:
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        workflow = data.get("workflow", [])
        logger.info("加载 Workflow: %s (%d 步骤)", filepath, len(workflow))
        return workflow
    except Exception:
        logger.warning("解析 workflow.json 失败: %s", filepath, exc_info=True)
        return None


def _parse_yaml_frontmatter(content: str) -> dict | None:
    match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    if not match:
        return None
    try:
        return yaml.safe_load(match.group(1)) or {}
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════════════════
# 查询接口
# ═══════════════════════════════════════════════════════════════════════════

def get_all_triggers() -> dict[str, str]:
    """返回 {trigger_keyword: skill_name} 映射。"""
    skills = load_skills()
    trigger_map = {}
    for name, skill in skills.items():
        for trigger in skill.get("triggers", []):
            trigger_map[trigger] = name
    return trigger_map


def get_user_skills() -> dict:
    """返回仅面向用户的 skills。"""
    skills = load_skills()
    return {k: v for k, v in skills.items() if v.get("user_invocable", True)}


def get_user_triggers() -> dict[str, str]:
    """返回仅面向用户的 trigger 映射。"""
    user_skills = get_user_skills()
    trigger_map = {}
    for name, skill in user_skills.items():
        for trigger in skill.get("triggers", []):
            trigger_map[trigger] = name
    return trigger_map


def get_skill_workflow(skill_name: str) -> list | None:
    skills = load_skills()
    skill = skills.get(skill_name)
    return skill.get("workflow") if skill else None


def get_report_workflow() -> list | None:
    return get_skill_workflow("ai-pr-medical-report")


def find_matching_skill(text: str) -> str | None:
    """根据用户输入匹配面向用户的 skill trigger。"""
    triggers = get_user_triggers()
    for trigger, skill_name in triggers.items():
        if trigger in text:
            return skill_name
    return None


def get_available_skills_context() -> str:
    """返回用户可见 skills 的摘要，注入 LLM system prompt。"""
    user_skills = get_user_skills()
    if not user_skills:
        return ""
    lines = ["7. **系统可用功能模块**："]
    for name, skill in user_skills.items():
        triggers_str = "、".join(skill.get("triggers", [])[:3])
        lines.append(f"- {skill['description']}（触发词: {triggers_str}）")
    return "\n".join(lines)
