"""Load and validate an agentpack project from disk.

Source layout (what plugin authors write):

    my-plugin/
    ├── agentpack.yaml          # single source of truth for metadata
    ├── skills/
    │   └── <skill-name>/
    │       ├── SKILL.md        # YAML frontmatter + Markdown body
    │       └── ...             # optional scripts / references / assets
    ├── commands/               # optional flat .md slash-commands
    │   └── <command>.md
    ├── agents/                 # optional subagent definitions (.md)
    │   └── <agent>.md
    └── hooks/hooks.json        # optional Claude Code hooks (passed through)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import frontmatter, miniyaml

CONFIG_NAMES = ("agentpack.yaml", "agentpack.yml")
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
VERSION_RE = re.compile(r"^\d+\.\d+\.\d+([-.+][0-9A-Za-z.-]+)?$")


class ProjectError(ValueError):
    pass


@dataclass
class Issue:
    level: str  # "error" | "warning"
    where: str
    message: str

    def __str__(self) -> str:
        return f"[{self.level.upper()}] {self.where}: {self.message}"


@dataclass
class Skill:
    name: str
    directory: Path
    frontmatter: Dict[str, Any]
    body: str
    extra_files: List[Path] = field(default_factory=list)

    @property
    def description(self) -> str:
        return str(self.frontmatter.get("description", ""))


@dataclass
class MarkdownItem:
    """A flat markdown component: a command or an agent definition."""

    name: str
    path: Path
    frontmatter: Dict[str, Any]
    body: str


@dataclass
class Project:
    root: Path
    config: Dict[str, Any]
    skills: List[Skill] = field(default_factory=list)
    commands: List[MarkdownItem] = field(default_factory=list)
    agents: List[MarkdownItem] = field(default_factory=list)
    hooks_file: Optional[Path] = None
    mcp_file: Optional[Path] = None

    @property
    def name(self) -> str:
        return str(self.config.get("name", ""))

    @property
    def version(self) -> str:
        return str(self.config.get("version", "0.0.0"))

    @property
    def description(self) -> str:
        return str(self.config.get("description", ""))

    def target_names(self) -> List[str]:
        targets = self.config.get("targets")
        if not targets:
            from .targets import DEFAULT_TARGETS

            return list(DEFAULT_TARGETS)
        if isinstance(targets, str):
            return [t.strip() for t in targets.split(",") if t.strip()]
        return [str(t) for t in targets]


def find_config(root: Path) -> Optional[Path]:
    for name in CONFIG_NAMES:
        candidate = root / name
        if candidate.is_file():
            return candidate
    return None


def load_project(root: Path) -> Project:
    root = root.resolve()
    config_path = find_config(root)
    if config_path is None:
        raise ProjectError(
            f"no agentpack.yaml found in {root}. Run 'agentpack init' to create one."
        )
    try:
        config = miniyaml.loads(config_path.read_text(encoding="utf-8"))
    except miniyaml.MiniYamlError as exc:
        raise ProjectError(f"{config_path.name}: {exc}") from exc
    if not isinstance(config, dict):
        raise ProjectError(f"{config_path.name}: top level must be a mapping")

    project = Project(root=root, config=config)
    _load_skills(project)
    _load_markdown_dir(project, "commands", project.commands)
    _load_markdown_dir(project, "agents", project.agents)

    hooks = root / "hooks" / "hooks.json"
    if hooks.is_file():
        project.hooks_file = hooks
    mcp = root / ".mcp.json"
    if mcp.is_file():
        project.mcp_file = mcp
    return project


def _load_skills(project: Project) -> None:
    skills_dir = project.root / "skills"
    if not skills_dir.is_dir():
        return
    for entry in sorted(skills_dir.iterdir()):
        if not entry.is_dir():
            continue
        skill_md = entry / "SKILL.md"
        if not skill_md.is_file():
            continue
        text = skill_md.read_text(encoding="utf-8")
        try:
            fm, body = frontmatter.split(text)
        except frontmatter.FrontmatterError as exc:
            raise ProjectError(f"skills/{entry.name}/SKILL.md: {exc}") from exc
        extra = [
            p
            for p in sorted(entry.rglob("*"))
            if p.is_file() and p.name != "SKILL.md"
        ]
        project.skills.append(
            Skill(
                name=str(fm.get("name", entry.name)),
                directory=entry,
                frontmatter=fm,
                body=body,
                extra_files=extra,
            )
        )


def _load_markdown_dir(project: Project, dirname: str, bucket: List[MarkdownItem]) -> None:
    directory = project.root / dirname
    if not directory.is_dir():
        return
    for path in sorted(directory.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        try:
            fm, body = frontmatter.split(text)
        except frontmatter.FrontmatterError as exc:
            raise ProjectError(f"{dirname}/{path.name}: {exc}") from exc
        bucket.append(MarkdownItem(name=path.stem, path=path, frontmatter=fm, body=body))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate(project: Project) -> List[Issue]:
    issues: List[Issue] = []

    def error(where: str, message: str) -> None:
        issues.append(Issue("error", where, message))

    def warning(where: str, message: str) -> None:
        issues.append(Issue("warning", where, message))

    cfg = project.config
    if not project.name:
        error("agentpack.yaml", "missing required field 'name'")
    elif not NAME_RE.match(project.name):
        error(
            "agentpack.yaml",
            f"name {project.name!r} must be kebab-case (lowercase letters, digits, hyphens)",
        )
    if not project.description:
        warning("agentpack.yaml", "missing 'description' — marketplaces display it")
    if "version" in cfg and not VERSION_RE.match(str(cfg["version"])):
        error("agentpack.yaml", f"version {cfg['version']!r} is not semver (e.g. 1.0.0)")

    from .targets import TARGETS

    for target in project.target_names():
        if target not in TARGETS:
            error(
                "agentpack.yaml",
                f"unknown target {target!r}; available: {', '.join(sorted(TARGETS))}",
            )

    if not project.skills and not project.commands and not project.agents:
        error(
            "project",
            "nothing to package: no skills/, commands/ or agents/ content found",
        )

    seen_names = set()
    for skill in project.skills:
        where = f"skills/{skill.directory.name}/SKILL.md"
        fm = skill.frontmatter
        if "name" not in fm:
            warning(where, "frontmatter has no 'name'; the folder name will be used")
        elif str(fm["name"]) != skill.directory.name:
            error(
                where,
                f"frontmatter name {fm['name']!r} must match folder name "
                f"{skill.directory.name!r} (required by Cursor and Copilot)",
            )
        if not NAME_RE.match(skill.name):
            error(where, f"skill name {skill.name!r} must be kebab-case")
        if skill.name in seen_names:
            error(where, f"duplicate skill name {skill.name!r}")
        seen_names.add(skill.name)
        if not fm.get("description"):
            error(
                where,
                "missing 'description' — agents rely on it to decide when to load the skill",
            )
        elif len(str(fm["description"])) > 1024:
            warning(where, "description longer than 1024 characters may be truncated")
        if not skill.body.strip():
            warning(where, "skill body is empty")

    for item in project.commands:
        where = f"commands/{item.path.name}"
        if not NAME_RE.match(item.name):
            error(where, f"command file name {item.name!r} must be kebab-case")
        if not item.frontmatter.get("description"):
            warning(where, "missing 'description' in frontmatter")

    for item in project.agents:
        where = f"agents/{item.path.name}"
        if not item.frontmatter.get("description"):
            warning(where, "missing 'description' in frontmatter")

    if project.hooks_file is not None:
        try:
            json.loads(project.hooks_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error("hooks/hooks.json", f"invalid JSON: {exc}")
    if project.mcp_file is not None:
        try:
            json.loads(project.mcp_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            error(".mcp.json", f"invalid JSON: {exc}")

    return issues
