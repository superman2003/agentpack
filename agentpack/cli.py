"""agentpack command-line interface.

Commands:
  agentpack init [dir]        scaffold a new project
  agentpack validate [dir]    lint agentpack.yaml and all skills
  agentpack build [dir]       generate dist/<target>/ bundles
  agentpack targets           list available targets
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .project import ProjectError, load_project, validate
from .scaffold import scaffold_project
from .targets import DEFAULT_TARGETS, TARGETS, build_all


def _cmd_init(args: argparse.Namespace) -> int:
    root = Path(args.directory).resolve()
    try:
        created = scaffold_project(root, name=args.name, force=args.force)
    except FileExistsError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(f"Initialized agentpack project in {root}")
    for path in created:
        print(f"  created {path.relative_to(root)}")
    print("\nNext steps:")
    print("  1. Edit agentpack.yaml (name, description, author)")
    print("  2. Write your skill in skills/example-skill/SKILL.md")
    print("  3. Run: agentpack build")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    try:
        project = load_project(Path(args.directory))
    except ProjectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    issues = validate(project)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    for issue in issues:
        print(str(issue))
    print(
        f"\n{project.name or '(unnamed)'}: {len(project.skills)} skill(s), "
        f"{len(project.commands)} command(s), {len(project.agents)} agent(s) — "
        f"{len(errors)} error(s), {len(warnings)} warning(s)"
    )
    return 1 if errors else 0


def _cmd_build(args: argparse.Namespace) -> int:
    try:
        project = load_project(Path(args.directory))
    except ProjectError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    issues = validate(project)
    errors = [i for i in issues if i.level == "error"]
    for issue in issues:
        print(str(issue))
    if errors:
        print(f"\nbuild aborted: {len(errors)} validation error(s)", file=sys.stderr)
        return 1

    if args.target:
        targets = []
        for chunk in args.target:
            targets.extend(t.strip() for t in chunk.split(",") if t.strip())
    else:
        targets = project.target_names()
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        print(
            f"error: unknown target(s): {', '.join(unknown)}; "
            f"available: {', '.join(sorted(TARGETS))}",
            file=sys.stderr,
        )
        return 1

    dist_dir = Path(args.out) if args.out else project.root / "dist"
    results = build_all(project, dist_dir, targets)

    total = 0
    for result in results:
        print(f"\n[{result.target}] -> {result.out_dir}")
        for path in result.files:
            print(f"  {path.relative_to(result.out_dir)}")
        for note in result.notes:
            print(f"  note: {note}")
        total += len(result.files)
    print(f"\nBuilt {len(results)} target(s), {total} file(s) in {dist_dir}")
    return 0


def _cmd_targets(_args: argparse.Namespace) -> int:
    descriptions = {
        "claude": "Claude Code plugin + marketplace.json (.claude-plugin/)",
        "cursor": "Cursor skills tree (.cursor/skills/)",
        "codex": "OpenAI Codex CLI skills tree (.codex/skills/)",
        "copilot": "GitHub Copilot skills tree (.github/skills/)",
        "agents": "Vendor-neutral skills tree (.agents/skills/)",
    }
    for name in DEFAULT_TARGETS:
        print(f"  {name:<10} {descriptions.get(name, '')}")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="agentpack",
        description=(
            "Write your agent skills once, ship them everywhere: "
            "Cursor, Claude Code, Codex, GitHub Copilot and any "
            "SKILL.md-compatible agent."
        ),
    )
    parser.add_argument("--version", action="version", version=f"agentpack {__version__}")
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="scaffold a new agentpack project")
    p_init.add_argument("directory", nargs="?", default=".", help="project directory")
    p_init.add_argument("--name", help="plugin name (kebab-case); defaults to directory name")
    p_init.add_argument("--force", action="store_true", help="overwrite existing files")
    p_init.set_defaults(func=_cmd_init)

    p_validate = sub.add_parser("validate", help="lint the project without building")
    p_validate.add_argument("directory", nargs="?", default=".", help="project directory")
    p_validate.set_defaults(func=_cmd_validate)

    p_build = sub.add_parser("build", help="generate per-platform bundles into dist/")
    p_build.add_argument("directory", nargs="?", default=".", help="project directory")
    p_build.add_argument(
        "-t", "--target", action="append",
        help="target(s) to build (repeatable or comma-separated); default: all",
    )
    p_build.add_argument("-o", "--out", help="output directory (default: <project>/dist)")
    p_build.set_defaults(func=_cmd_build)

    p_targets = sub.add_parser("targets", help="list available build targets")
    p_targets.set_defaults(func=_cmd_targets)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 0
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
