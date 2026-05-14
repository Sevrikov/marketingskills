from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.agent_skill import AgentSkill, AgentSkillStatus


@dataclass(frozen=True)
class ParsedSkill:
    name: str
    slug: str
    description: str
    version: str | None
    source_path: str
    body: str
    metadata_json: dict[str, Any]


@dataclass(frozen=True)
class SkillSyncResult:
    scanned: int
    upserted: int
    archived: int


class InvalidSkillFile(ValueError):
    pass


def list_agent_skills(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    status: str | None = AgentSkillStatus.ACTIVE.value,
) -> list[AgentSkill]:
    stmt = select(AgentSkill).order_by(AgentSkill.name.asc())
    if status:
        stmt = stmt.where(AgentSkill.status == status)
    stmt = stmt.limit(limit).offset(offset)
    return list(db.scalars(stmt))


def get_agent_skill(db: Session, skill_id: str) -> AgentSkill | None:
    return db.get(AgentSkill, skill_id)


def get_agent_skill_by_name(db: Session, name: str) -> AgentSkill | None:
    stmt = select(AgentSkill).where(AgentSkill.name == name).limit(1)
    return db.scalars(stmt).first()


def sync_agent_skills(db: Session, skills_root: str | Path) -> SkillSyncResult:
    root = Path(skills_root)
    parsed_skills = scan_skill_files(root)
    existing_by_name = {skill.name: skill for skill in db.scalars(select(AgentSkill))}

    upserted = 0
    active_names: set[str] = set()
    for parsed in parsed_skills:
        active_names.add(parsed.name)
        skill = existing_by_name.get(parsed.name)
        values = {
            "slug": parsed.slug,
            "description": parsed.description,
            "version": parsed.version,
            "source_path": parsed.source_path,
            "body": parsed.body,
            "metadata_json": parsed.metadata_json,
            "status": AgentSkillStatus.ACTIVE.value,
        }
        if skill is None:
            db.add(AgentSkill(name=parsed.name, **values))
        else:
            for field, value in values.items():
                setattr(skill, field, value)
        upserted += 1

    archived = 0
    for skill in existing_by_name.values():
        if skill.name not in active_names and skill.status != AgentSkillStatus.ARCHIVED.value:
            skill.status = AgentSkillStatus.ARCHIVED.value
            archived += 1

    db.commit()
    return SkillSyncResult(scanned=len(parsed_skills), upserted=upserted, archived=archived)


def scan_skill_files(skills_root: str | Path) -> list[ParsedSkill]:
    root = Path(skills_root)
    if not root.exists():
        return []
    skill_files = sorted(root.glob("*/SKILL.md"))
    return [parse_skill_file(path) for path in skill_files]


def parse_skill_file(path: Path) -> ParsedSkill:
    content = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    frontmatter, body = _split_frontmatter(content, path)
    metadata = _parse_simple_yaml(frontmatter)

    name = str(metadata.get("name") or path.parent.name).strip()
    description = str(metadata.get("description") or "").strip()
    nested_metadata = metadata.get("metadata")
    if not isinstance(nested_metadata, dict):
        nested_metadata = {}
    version = nested_metadata.get("version")

    if not name:
        raise InvalidSkillFile(f"Skill file {path} does not define a name.")
    if not description:
        raise InvalidSkillFile(f"Skill file {path} does not define a description.")

    return ParsedSkill(
        name=name,
        slug=path.parent.name,
        description=description,
        version=str(version) if version is not None else None,
        source_path=str(path.resolve()),
        body=body.strip(),
        metadata_json=metadata,
    )


def _split_frontmatter(content: str, path: Path) -> tuple[str, str]:
    if not content.startswith("---\n"):
        raise InvalidSkillFile(f"Skill file {path} must start with YAML frontmatter.")
    end = content.find("\n---\n", 4)
    if end == -1:
        raise InvalidSkillFile(f"Skill file {path} has no closing frontmatter marker.")
    return content[4:end], content[end + len("\n---\n") :]


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    result: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, result)]

    for raw_line in text.splitlines():
        if not raw_line.strip() or raw_line.lstrip().startswith("#"):
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        stripped = raw_line.strip()
        if ":" not in stripped:
            continue
        key, value = stripped.split(":", 1)
        key = key.strip()
        value = value.strip()

        while stack and indent <= stack[-1][0]:
            stack.pop()
        current = stack[-1][1]

        if value == "":
            child: dict[str, Any] = {}
            current[key] = child
            stack.append((indent, child))
        else:
            current[key] = _parse_scalar(value)

    return result


def _parse_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if value in {"null", "None"}:
        return None
    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]
    return value
