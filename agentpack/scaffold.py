"""Scaffold a new agentpack project (`agentpack init`)."""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

_CONFIG_TEMPLATE = """\
# agentpack.yaml — single source of truth for your plugin metadata.
# Run `agentpack build` to generate bundles for every platform.

name: {name}
version: 0.1.0
description: One sentence on what this plugin does and when an agent should use it.

author:
  name: Your Name
  url: https://github.com/your-name

license: MIT
# repository: https://github.com/your-name/{name}
# homepage: https://github.com/your-name/{name}

keywords:
  - example

# Platforms to build. Remove entries you don't care about,
# or override at build time with `agentpack build -t cursor,claude`.
targets:
  - claude
  - cursor
  - codex
  - copilot
  - agents
"""

_SKILL_TEMPLATE = """\
---
name: example-skill
description: Explain when this skill applies and what it helps the agent do. Agents read this line to decide whether to load the skill, so make it specific.
---

# Example skill

Replace this with real instructions for the agent.

## Instructions

- Step-by-step guidance for the agent
- Domain-specific conventions and footguns
- Reference extra files in this folder if needed, e.g. `references/details.md`
"""

_COMMAND_TEMPLATE = """\
---
description: Example slash command. Invoke with /example-command.
---

When this command is invoked, do the following:

1. Describe the workflow step by step.
2. Keep it to a single focused task.
"""

_GITIGNORE = """\
dist/
__pycache__/
"""


def scaffold_project(root: Path, name: Optional[str] = None, force: bool = False) -> List[Path]:
    name = name or root.name.lower().replace("_", "-").replace(" ", "-")
    files = {
        root / "agentpack.yaml": _CONFIG_TEMPLATE.format(name=name),
        root / "skills" / "example-skill" / "SKILL.md": _SKILL_TEMPLATE,
        root / "commands" / "example-command.md": _COMMAND_TEMPLATE,
        root / ".gitignore": _GITIGNORE,
    }
    existing = [p for p in files if p.exists()]
    if existing and not force:
        rels = ", ".join(str(p.relative_to(root)) for p in existing)
        raise FileExistsError(f"refusing to overwrite {rels} (use --force)")

    created: List[Path] = []
    for path, content in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(content)
        created.append(path)
    return created
