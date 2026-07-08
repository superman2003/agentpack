# agentpack

[English](README.md) | **简体中文** | [日本語](README.ja.md)

**技能只写一份，发布到所有 AI 编程助手。**

每个 AI 编程助手都发明了自己的插件目录：Cursor 读 `.cursor/skills/`，Claude Code 读 `.claude-plugin/` + `skills/`，Codex 读 `.codex/skills/`，GitHub Copilot 读 `.github/skills/`，厂商中立标准又是 `.agents/skills/`。如果你维护一个技能包或插件，就得手工同步五份几乎一样的内容。

agentpack 是"agent 插件界的 Babel"：你只维护**一份**源文件——一个 `SKILL.md` 目录加一个 `agentpack.yaml`——一条命令生成所有平台可直接发布的产物，包括 Claude Code 的 `plugin.json` 清单和 `marketplace.json`。

- **零依赖。** 纯 Python 标准库，`pip install` 即用。
- **先校验后构建。** 提前抓住缺 description、frontmatter 名字与文件夹不一致、名字不是 kebab-case、JSON 损坏等会让技能对 agent"隐身"的问题。
- **懂各平台方言。** 平台不支持的 frontmatter 字段自动剔除并提示；`globs` 自动映射为 Cursor 的 `paths`；斜杠命令在没有 commands 目录的平台自动转成手动触发的技能。
- **Windows 优先。** 在 Windows、Linux、macOS 上开发和测试。

## 安装

```bash
pip install skillpack   # 安装后命令名仍是 agentpack
# 或从源码安装：
git clone https://github.com/superman2003/agentpack && cd agentpack && pip install .
```

## 快速开始

```bash
# 创建项目脚手架
agentpack init my-toolkit --name my-toolkit
cd my-toolkit

# 编辑 agentpack.yaml 和 skills/example-skill/SKILL.md，然后：
agentpack validate
agentpack build
```

`agentpack build` 生成：

```
dist/
├── claude/                          # Claude Code 插件 + marketplace
│   ├── .claude-plugin/marketplace.json
│   └── my-toolkit/
│       ├── .claude-plugin/plugin.json
│       ├── skills/<name>/SKILL.md
│       └── commands/<name>.md
├── cursor/.cursor/skills/<name>/SKILL.md
├── codex/.codex/skills/<name>/SKILL.md
├── copilot/.github/skills/<name>/SKILL.md
└── agents/.agents/skills/<name>/SKILL.md   # 厂商中立标准
```

把对应平台的目录树拷进你的仓库（或用 `--plugin-dir` 让 Claude Code 直接加载插件），就完成发布了。

## 源文件布局

你只需要写这一份：

```
my-toolkit/
├── agentpack.yaml           # 名称、版本、描述、作者、目标平台
├── skills/
│   └── review-pr/
│       ├── SKILL.md         # YAML frontmatter + Markdown 指令
│       └── references/…     # 可选附加文件，原样复制
├── commands/                # 可选的扁平斜杠命令（.md）
├── agents/                  # 可选的 Claude Code 子代理（.md）
├── hooks/hooks.json         # 可选的 Claude Code 钩子（透传）
└── .mcp.json                # 可选的 MCP 服务器配置（透传）
```

### agentpack.yaml

```yaml
name: my-toolkit            # kebab-case，必填
version: 1.0.0              # 语义化版本
description: 这个插件做什么、agent 什么时候该用它。
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
name: review-pr            # 必须与文件夹名一致
description: 当被要求审查 PR 或 diff 时使用。
paths: "**/*.py"           # 可选；Cursor 风格的文件范围限定
---

# 给 agent 的指令……
```

## 命令

| 命令 | 作用 |
| --- | --- |
| `agentpack init [dir]` | 创建新项目脚手架 |
| `agentpack validate [dir]` | 校验配置和技能；有错误时退出码为 1 |
| `agentpack build [dir]` | 生成 `dist/<target>/` 产物 |
| `agentpack build -t cursor,claude` | 只构建指定平台 |
| `agentpack targets` | 列出支持的平台 |

## 平台差异如何处理

| 概念 | claude | cursor | codex | copilot | agents |
| --- | --- | --- | --- | --- | --- |
| 技能 | 插件内 `skills/` | `.cursor/skills/` | `.codex/skills/` | `.github/skills/` | `.agents/skills/` |
| 斜杠命令 | `commands/*.md` | 转为手动技能 | 转换 | 转换 | 转换 |
| `paths` / `globs` 范围限定 | 剔除（不支持） | 保留（`globs`→`paths`） | 剔除 | 剔除 | 保留 |
| 子代理（`agents/`） | 输出 | 跳过 | 跳过 | 跳过 | 跳过 |
| 钩子 / MCP 配置 | 输出 | 跳过 | 跳过 | 跳过 | 跳过 |
| 清单 | `plugin.json` + `marketplace.json` | — | — | — | — |

所有被剔除或转换的内容都会在构建时以 `note:` 形式打印出来，不会有任何静默行为。

## 示例

完整可运行的示例在 [`examples/code-review-toolkit/`](examples/code-review-toolkit/)，构建方式：

```bash
agentpack build examples/code-review-toolkit
```

## 开发

```bash
python -m unittest discover tests -v
```

测试同样不需要任何依赖。

## 许可证

MIT
