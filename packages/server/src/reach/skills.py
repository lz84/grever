"""
Grever 技能库 API — 技能扫描、下载、安装指令生成

提供:
- 技能列表 / 技能详情（已有）
- 技能文件原始下载 /api/v1/skills/{id}/raw/{filename}
- 安装指令生成 /api/v1/skills/{id}/install-prompt

Agent 通过 URL 从 Grever 拉取技能，不依赖本地路径。
"""
import os
import re
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/skills", tags=["skills"])

# Grever project root
NEXUS_ROOT = Path(__file__).resolve().parents[4]

# Single source of truth: all skills live in skills/
SKILLS_DIR = NEXUS_ROOT / "skills"

# Grever base URL for agent installation (env override for production)
GREVER_BASE_URL = os.environ.get("GREVER_BASE_URL", "http://localhost:8091")

class SkillInfo(BaseModel):
    id: str
    name: str
    description: str
    category: str = "通用"
    installed: bool = True
    path: str = ""
    source: str = ""
    install_url: str = ""

def _parse_skill_md(skill_dir: Path) -> dict | None:
    """Parse SKILL.md to extract name, description, category."""
    skill_file = None
    for f in skill_dir.iterdir():
        if f.name.lower() == "skill.md":
            skill_file = f
            break

    if not skill_file:
        return None

    content = skill_file.read_text(encoding="utf-8", errors="replace")

    description = ""
    name = skill_dir.name

    # YAML frontmatter description
    desc_match = re.search(r'^description:\s*(.+)$', content, re.MULTILINE)
    if desc_match:
        description = desc_match.group(1).strip().strip('"').strip("'")[:200]

    # Name from frontmatter or header
    name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
    if name_match:
        name = name_match.group(1).strip()
    else:
        header_match = re.search(r'# (.+?)(\n|$)', content)
        if header_match:
            name = header_match.group(1).strip()

    category = _categorize(skill_dir.name, name, description)

    skill_url = f"{GREVER_BASE_URL}/api/v1/skills/{skill_dir.name}"

    return {
        "id": skill_dir.name,
        "name": name,
        "description": description or "暂无描述",
        "category": category,
        "installed": True,
        "path": str(skill_dir),
        "source": "Grever",
        "install_url": skill_url,
    }

def _categorize(dir_name: str, name: str, description: str) -> str:
    """Determine skill category based on name/description."""
    text = f"{dir_name} {name} {description}".lower()
    if "executor" in text or ("执行" in name and "基础设施" not in name):
        return "执行"
    elif "genesis" in text or "分解" in text or "decompos" in text:
        return "协调"
    elif "reins" in text or "crud" in text or "实体" in text:
        return "协调"
    elif "pulse" in text or "心跳" in text or "lifecycle" in text or "息" in text:
        return "基础设施"
    elif "grasp" in text or "认知" in text or "knowledge" in text or "悟" in text:
        return "认知"
    elif "verifier" in text or "验证" in text or "鉴" in text:
        return "验证"
    return "通用"

@router.get("")
def list_skills(category: str = "", q: str = ""):
    """列出所有 Grever 自带技能"""
    skills = []
    if not SKILLS_DIR.exists():
        return {"skills": [], "total": 0}

    for item in sorted(SKILLS_DIR.iterdir()):
        if not item.is_dir() or item.name.startswith("_") or item.name.startswith("."):
            continue

        info = _parse_skill_md(item)
        if not info:
            continue

        if category and info["category"] != category:
            continue
        if q and q.lower() not in info["name"].lower() and q.lower() not in info["description"].lower():
            continue

        skills.append(info)

    return {"skills": skills, "total": len(skills)}

@router.get("/{skill_id}")
def get_skill(skill_id: str):
    """获取单个技能详情（含 SKILL.md 内容）"""
    if not SKILLS_DIR.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    info = _parse_skill_md(skill_dir)
    if not info:
        raise HTTPException(404, f"Skill not found: {skill_id}")

    skill_file = None
    for f in skill_dir.iterdir():
        if f.name.lower() == "skill.md":
            skill_file = f
            break

    if skill_file:
        info["content"] = skill_file.read_text(encoding="utf-8", errors="replace")[:5000]

    return info

@router.get("/{skill_id}/raw/{filename}")
def get_skill_file_raw(skill_id: str, filename: str):
    """下载技能目录下的单个文件（原始内容）"""
    if not SKILLS_DIR.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    filepath = skill_dir / filename
    if not filepath.exists() or not filepath.is_file():
        raise HTTPException(404, f"File not found: {filename}")

    # 防止路径穿越
    try:
        filepath.resolve().relative_to(skill_dir.resolve())
    except ValueError:
        raise HTTPException(403, "Access denied")

    # 返回文本内容（SKILL.md, skill.py 等）
    try:
        content = filepath.read_text(encoding="utf-8")
        return PlainTextResponse(content=content)
    except UnicodeDecodeError:
        # 二进制文件（图片等）返回 base64 提示
        raise HTTPException(400, f"Binary file not supported for raw download: {filename}")

@router.get("/{skill_id}/install-prompt", response_class=PlainTextResponse)
def get_install_prompt(skill_id: str):
    """生成安装技能的 prompt 指令文本，用于复制到剪贴板"""
    if not SKILLS_DIR.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    info = _parse_skill_md(skill_dir)
    if not info:
        raise HTTPException(404, f"Skill not found: {skill_id}")

    # 列出技能目录下的文件
    files = [f.name for f in skill_dir.iterdir() if f.is_file()
             and not f.name.startswith("_") and f.suffix != ".pyc"]

    skill_url = f"{GREVER_BASE_URL}/api/v1/skills/{skill_id}"
    file_urls = "\n".join([
        f"   - {f}: {skill_url}/raw/{f}" for f in sorted(files)
    ])

    # 根据技能类型生成环境变量提示
    env_vars = {
        "executor": "NEXUS_SERVER_URL, NEXUS_AGENT_ID, NEXUS_CAPABILITIES",
        "pulse": "NEXUS_SERVER_URL, NEXUS_AGENT_ID, NEXUS_AGENT_NAME, NEXUS_CAPABILITIES",
        "genesis": "NEXUS_SERVER_URL, LLM_API (可选), GRASP_API (可选)",
        "reins": "NEXUS_SERVER_URL",
        "verifier": "NEXUS_SERVER_URL, LLM_API (llm 验证时需要)",
        "grasp": "NEXUS_SERVER_URL",
    }

    env_hint = env_vars.get(skill_id, "NEXUS_SERVER_URL")

    prompt = f"""请安装 Grever 技能 "{info['name']}"（{skill_id}）。

技能信息：
- 名称: {info['name']}
- 描述: {info['description']}
- 技能目录: {skill_url}

安装步骤：
1. 从 Grever 下载以下文件到你的 skills/{skill_id}/ 目录：
{file_urls}

2. 确保你的 skills/{skill_id}/SKILL.md 和对应的脚本文件已就位。

3. 设置以下环境变量后重启：
   - {env_hint}

4. 安装完成后，你应该能使用该技能的功能。"""

    return prompt

@router.get("/{skill_id}/files")
def get_skill_files(skill_id: str):
    """获取技能目录下的文件列表"""
    if not SKILLS_DIR.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    skill_dir = SKILLS_DIR / skill_id
    if not skill_dir.exists():
        raise HTTPException(404, f"Skill not found: {skill_id}")

    files = []
    for f in skill_dir.iterdir():
        if f.is_file() and not f.name.startswith("_"):
            files.append({
                "name": f.name,
                "size": f.stat().st_size,
                "url": f"{GREVER_BASE_URL}/api/v1/skills/{skill_id}/raw/{f.name}",
            })

    return {"skill_id": skill_id, "files": files, "total": len(files)}
