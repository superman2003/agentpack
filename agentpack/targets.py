"""Target generators: turn one agentpack project into per-platform bundles.

Each generator receives the loaded Project and an output directory and
writes a ready-to-ship layout for that platform:

  claude    Claude Code plugin (.claude-plugin/plugin.json + components)
            plus a marketplace.json so the repo doubles as a marketplace
  cursor    .cursor/skills/ tree (Cursor also loads commands as skills)
  codex     .codex/skills/ tree for OpenAI Codex CLI
  copilot   .github/skills/ tree for GitHub Copilot
  agents    vendor-neutral .agents/skills/ tree (agentskills.io layout)
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Callable, Dict, List

from . import frontmatter
from .project import MarkdownItem, Project, Skill

# Frontmatter keys each platform understands; everything else is dropped
# (reported by the builder) so we never emit fields a host will choke on.
_SKILL_KEYS = {
    "claude": {"name", "description", "license", "allowed-tools", "metadata",
               "disable-model-invocation"},
    "cursor": {"name", "description", "paths", "globs", "disable-model-invocation",
               "metadata", "license"},
    "codex": {"name", "description", "license", "metadata", "allowed-tools",
              "disable-model-invocation"},
    "copilot": {"name", "description", "license", "allowed-tools"},
    "agents": None,  # vendor-neutral: keep everything
}


class BuildResult:
    def __init__(self, target: str, out_dir: Path):
        self.target = target
        self.out_dir = out_dir
        self.files: List[Path] = []
        self.notes: List[str] = []

    def wrote(self, path: Path) -> None:
        self.files.append(path)


def _write_text(result: BuildResult, path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    result.wrote(path)


def _write_json(result: BuildResult, path: Path, data: Any) -> None:
    _write_text(result, path, json.dumps(data, indent=2, ensure_ascii=False) + "\n")


def _copy_file(result: BuildResult, src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    result.wrote(dst)


def _filter_frontmatter(fm: Dict[str, Any], target: str, result: BuildResult,
                        where: str) -> Dict[str, Any]:
    allowed = _SKILL_KEYS.get(target)
    if allowed is None:
        return dict(fm)
    kept: Dict[str, Any] = {}
    dropped: List[str] = []
    for key, value in fm.items():
        if key in allowed:
            kept[key] = value
        else:
            dropped.append(key)
    if target == "cursor" and "globs" in kept and "paths" not in kept:
        kept["paths"] = kept.pop("globs")
    if dropped:
        result.notes.append(
            f"{where}: dropped frontmatter not supported by {target}: {', '.join(dropped)}"
        )
    return kept


def _emit_skill(result: BuildResult, skill: Skill, skills_root: Path, target: str) -> None:
    skill_dir = skills_root / skill.directory.name
    fm = _filter_frontmatter(
        skill.frontmatter, target, result, f"skills/{skill.directory.name}"
    )
    fm.setdefault("name", skill.directory.name)
    fm.setdefault("description", skill.description or skill.directory.name)
    _write_text(result, skill_dir / "SKILL.md", frontmatter.join(fm, skill.body))
    for extra in skill.extra_files:
        rel = extra.relative_to(skill.directory)
        _copy_file(result, extra, skill_dir / rel)


def _command_as_skill(item: MarkdownItem) -> Skill:
    """Represent a flat command file as a manually-invoked skill."""
    fm = dict(item.frontmatter)
    fm["name"] = item.name
    fm.setdefault("description", f"Slash command /{item.name}")
    fm["disable-model-invocation"] = True
    return Skill(name=item.name, directory=item.path.parent / item.name,
                 frontmatter=fm, body=item.body, extra_files=[])


# ---------------------------------------------------------------------------
# Claude Code
# ---------------------------------------------------------------------------

def build_claude(project: Project, out_dir: Path) -> BuildResult:
    result = BuildResult("claude", out_dir)
    plugin_root = out_dir / project.name

    manifest: Dict[str, Any] = {"name": project.name}
    for src_key, dst_key in (
        ("version", "version"),
        ("description", "description"),
        ("homepage", "homepage"),
        ("license", "license"),
        ("keywords", "keywords"),
    ):
        if project.config.get(src_key):
            manifest[dst_key] = project.config[src_key]
    author = project.config.get("author")
    if isinstance(author, dict):
        manifest["author"] = author
    elif isinstance(author, str):
        manifest["author"] = {"name": author}
    repo = project.config.get("repository")
    if repo:
        manifest["repository"] = repo if isinstance(repo, dict) else {
            "type": "git", "url": str(repo)}
    _write_json(result, plugin_root / ".claude-plugin" / "plugin.json", manifest)

    for skill in project.skills:
        _emit_skill(result, skill, plugin_root / "skills", "claude")

    for item in project.commands:
        fm = {k: v for k, v in item.frontmatter.items()}
        _write_text(result, plugin_root / "commands" / f"{item.name}.md",
                    frontmatter.join(fm, item.body))

    for item in project.agents:
        _write_text(result, plugin_root / "agents" / f"{item.name}.md",
                    frontmatter.join(dict(item.frontmatter), item.body))

    if project.hooks_file is not None:
        _copy_file(result, project.hooks_file, plugin_root / "hooks" / "hooks.json")
    if project.mcp_file is not None:
        _copy_file(result, project.mcp_file, plugin_root / ".mcp.json")

    marketplace = {
        "name": project.config.get("marketplace-name", f"{project.name}-marketplace"),
        "owner": {"name": (manifest.get("author") or {}).get("name", project.name)},
        "plugins": [
            {
                "name": project.name,
                "source": f"./{project.name}",
                "description": project.description,
            }
        ],
    }
    _write_json(result, out_dir / ".claude-plugin" / "marketplace.json", marketplace)
    result.notes.append(
        "install locally with: claude --plugin-dir "
        + str(plugin_root)
    )
    return result


# ---------------------------------------------------------------------------
# Skill-tree targets (cursor / codex / copilot / agents)
# ---------------------------------------------------------------------------

def _build_skill_tree(project: Project, out_dir: Path, target: str,
                      skills_root_rel: str) -> BuildResult:
    result = BuildResult(target, out_dir)
    skills_root = out_dir / Path(skills_root_rel)

    for skill in project.skills:
        _emit_skill(result, skill, skills_root, target)

    # These hosts have no separate slash-command directory; ship commands as
    # manual-invocation skills so `/name` still works.
    for item in project.commands:
        _emit_skill(result, _command_as_skill(item), skills_root, target)
        result.notes.append(
            f"commands/{item.name}.md packaged as manual skill /{item.name}"
        )

    if project.agents:
        result.notes.append(
            f"agents/ definitions are Claude Code-specific and were skipped for {target}"
        )
    if project.hooks_file is not None:
        result.notes.append(f"hooks/hooks.json is Claude Code-specific; skipped for {target}")
    return result


def build_cursor(project: Project, out_dir: Path) -> BuildResult:
    return _build_skill_tree(project, out_dir, "cursor", ".cursor/skills")


def build_codex(project: Project, out_dir: Path) -> BuildResult:
    return _build_skill_tree(project, out_dir, "codex", ".codex/skills")


def build_copilot(project: Project, out_dir: Path) -> BuildResult:
    return _build_skill_tree(project, out_dir, "copilot", ".github/skills")


def build_agents(project: Project, out_dir: Path) -> BuildResult:
    return _build_skill_tree(project, out_dir, "agents", ".agents/skills")


TARGETS: Dict[str, Callable[[Project, Path], BuildResult]] = {
    "claude": build_claude,
    "cursor": build_cursor,
    "codex": build_codex,
    "copilot": build_copilot,
    "agents": build_agents,
}

DEFAULT_TARGETS = ["claude", "cursor", "codex", "copilot", "agents"]


def build_all(project: Project, dist_dir: Path, targets: List[str]) -> List[BuildResult]:
    results = []
    for name in targets:
        out_dir = dist_dir / name
        if out_dir.exists():
            shutil.rmtree(out_dir)
        results.append(TARGETS[name](project, out_dir))
    return results
