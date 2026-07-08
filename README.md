# agentpack

**Write your agent skills once. Ship them everywhere.**

Every AI coding agent invented its own plugin layout: Cursor reads `.cursor/skills/`, Claude Code reads `.claude-plugin/` + `skills/`, Codex reads `.codex/skills/`, GitHub Copilot reads `.github/skills/`, and the vendor-neutral standard uses `.agents/skills/`. If you maintain a skill pack or plugin, you end up hand-maintaining five slightly different copies of the same content.

agentpack is a Babel for agent plugins: you keep **one** source of truth — a folder of `SKILL.md` files plus a single `agentpack.yaml` — and one command generates correct, ready-to-publish bundles for every platform, including the Claude Code `plugin.json` manifest and `marketplace.json`.

- **Zero dependencies.** Pure Python standard library. `pip install` and go.
- **Validates before it builds.** Catches missing descriptions, name/folder mismatches, non-kebab-case names, broken JSON — the things that silently make a skill invisible to an agent.
- **Knows each platform's dialect.** Frontmatter fields a host doesn't support are dropped (and reported), `globs` is mapped to `paths` for Cursor, slash commands are converted to manual-invocation skills on platforms without a commands directory.
- **Windows-first.** Developed and tested on Windows, Linux and macOS.

## Install

```bash
pip install agentpack
# or from source:
git clone https://github.com/superman2003/agentpack && cd agentpack && pip install .
```

## Quick start

```bash
# scaffold a project
agentpack init my-toolkit --name my-toolkit
cd my-toolkit

# edit agentpack.yaml and skills/example-skill/SKILL.md, then:
agentpack validate
agentpack build
```

`agentpack build` produces:

```
dist/
├── claude/                          # Claude Code plugin + marketplace
│   ├── .claude-plugin/marketplace.json
│   └── my-toolkit/
│       ├── .claude-plugin/plugin.json
│       ├── skills/<name>/SKILL.md
│       └── commands/<name>.md
├── cursor/.cursor/skills/<name>/SKILL.md
├── codex/.codex/skills/<name>/SKILL.md
├── copilot/.github/skills/<name>/SKILL.md
└── agents/.agents/skills/<name>/SKILL.md   # vendor-neutral standard
```

Copy the tree for your platform into your repo (or point Claude Code at the plugin with `--plugin-dir`), and you're published.

## Source layout

You write this once:

```
my-toolkit/
├── agentpack.yaml           # name, version, description, author, targets
├── skills/
│   └── review-pr/
│       ├── SKILL.md         # YAML frontmatter + Markdown instructions
│       └── references/…     # optional extra files, copied verbatim
├── commands/                # optional flat slash-commands (.md)
├── agents/                  # optional Claude Code subagents (.md)
├── hooks/hooks.json         # optional Claude Code hooks (passed through)
└── .mcp.json                # optional MCP server config (passed through)
```

### agentpack.yaml

```yaml
name: my-toolkit            # kebab-case, required
version: 1.0.0              # semver
description: What this plugin does and when agents should use it.
author:
  name: Your Name
  url: https://github.com/your-name
license: MIT
keywords: [code-review, git]
targets: [claude, cursor, codex, copilot, agents]
```

### SKILL.md

```markdown
---
name: review-pr            # must match the folder name
description: Use when asked to review a pull request or diff.
paths: "**/*.py"           # optional; Cursor-style file scoping
---

# Instructions for the agent…
```

## Commands

| Command | What it does |
| --- | --- |
| `agentpack init [dir]` | Scaffold a new project |
| `agentpack validate [dir]` | Lint config and skills; exit 1 on errors |
| `agentpack build [dir]` | Generate `dist/<target>/` bundles |
| `agentpack build -t cursor,claude` | Build only selected targets |
| `agentpack targets` | List supported platforms |

## How platform differences are handled

| Concept | claude | cursor | codex | copilot | agents |
| --- | --- | --- | --- | --- | --- |
| Skills | `skills/` in plugin | `.cursor/skills/` | `.codex/skills/` | `.github/skills/` | `.agents/skills/` |
| Slash commands | `commands/*.md` | converted to manual skill | converted | converted | converted |
| `paths` / `globs` scoping | dropped (unsupported) | kept (`globs`→`paths`) | dropped | dropped | kept |
| Subagents (`agents/`) | shipped | skipped | skipped | skipped | skipped |
| Hooks / MCP config | shipped | skipped | skipped | skipped | skipped |
| Manifest | `plugin.json` + `marketplace.json` | — | — | — | — |

Everything dropped or converted is printed as a `note:` during the build, so there are no silent surprises.

## Example

A complete working example lives in [`examples/code-review-toolkit/`](examples/code-review-toolkit/). Build it with:

```bash
agentpack build examples/code-review-toolkit
```

## Development

```bash
python -m unittest discover tests -v
```

No dependencies needed, for tests either.

## License

MIT

---

# agentpack（中文说明）

**技能只写一份，发布到所有 AI 编程助手。**

每个 AI 编程助手都发明了自己的插件目录：Cursor 读 `.cursor/skills/`，Claude Code 读 `.claude-plugin/` + `skills/`，Codex 读 `.codex/skills/`，GitHub Copilot 读 `.github/skills/`，通用标准又是 `.agents/skills/`。维护一个技能包意味着手工同步五份几乎一样的内容。

agentpack 是"agent 插件界的 Babel"：你只维护**一份**源文件（若干 `SKILL.md` + 一个 `agentpack.yaml`），一条命令生成所有平台可直接发布的产物，包括 Claude Code 的 `plugin.json` 和 `marketplace.json`。

- **零依赖**，纯 Python 标准库；
- **先校验后构建**，提前发现缺 description、名字与文件夹不一致等会让技能"隐身"的问题；
- **懂各平台方言**：不支持的 frontmatter 字段自动剔除并提示，`globs` 自动映射为 Cursor 的 `paths`，斜杠命令在没有 commands 目录的平台自动转成手动触发的技能；
- **Windows 友好**，三平台 CI 测试。

## 快速开始

```bash
pip install agentpack
agentpack init my-toolkit --name my-toolkit
cd my-toolkit
# 编辑 agentpack.yaml 和 skills/example-skill/SKILL.md 后：
agentpack validate
agentpack build
```

构建产物在 `dist/` 下按平台分目录，直接拷进你的仓库即可发布。完整示例见 `examples/code-review-toolkit/`。
