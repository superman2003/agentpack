# agentpack

[English](README.md) | [简体中文](README.zh-CN.md) | **日本語**

**エージェントスキルを一度書けば、どこへでも配布できます。**

AI コーディングエージェントはそれぞれ独自のプラグイン構成を持っています。Cursor は `.cursor/skills/`、Claude Code は `.claude-plugin/` + `skills/`、Codex は `.codex/skills/`、GitHub Copilot は `.github/skills/`、そしてベンダー中立の標準は `.agents/skills/` を読み込みます。スキルパックやプラグインを維持するには、ほぼ同じ内容を 5 つ手作業で同期する必要がありました。

agentpack は「エージェントプラグインのための Babel」です。`SKILL.md` のフォルダと 1 つの `agentpack.yaml` という**単一の**ソースを維持するだけで、1 つのコマンドが Claude Code の `plugin.json` マニフェストや `marketplace.json` を含む、各プラットフォーム向けの公開可能なバンドルを生成します。

- **依存ゼロ。** 純粋な Python 標準ライブラリのみ。`pip install` してすぐ使えます。
- **ビルド前に検証。** description の欠落、名前とフォルダ名の不一致、kebab-case でない名前、壊れた JSON など、スキルがエージェントから「見えなくなる」問題を事前に検出します。
- **各プラットフォームの方言を理解。** サポートされない frontmatter フィールドは削除して報告し、`globs` は Cursor の `paths` にマッピング、スラッシュコマンドは commands ディレクトリのないプラットフォームでは手動起動スキルに変換します。
- **Windows ファースト。** Windows、Linux、macOS で開発・テストされています。

## インストール

```bash
pip install agent-pack   # `agentpack` コマンドがインストールされます
# またはソースから：
git clone https://github.com/superman2003/agentpack && cd agentpack && pip install .
```

## クイックスタート

```bash
# プロジェクトの雛形を作成
agentpack init my-toolkit --name my-toolkit
cd my-toolkit

# agentpack.yaml と skills/example-skill/SKILL.md を編集してから：
agentpack validate
agentpack build
```

`agentpack build` は以下を生成します：

```
dist/
├── claude/                          # Claude Code プラグイン + marketplace
│   ├── .claude-plugin/marketplace.json
│   └── my-toolkit/
│       ├── .claude-plugin/plugin.json
│       ├── skills/<name>/SKILL.md
│       └── commands/<name>.md
├── cursor/.cursor/skills/<name>/SKILL.md
├── codex/.codex/skills/<name>/SKILL.md
├── copilot/.github/skills/<name>/SKILL.md
└── agents/.agents/skills/<name>/SKILL.md   # ベンダー中立標準
```

対象プラットフォームのツリーをリポジトリにコピーする（または Claude Code に `--plugin-dir` で読み込ませる）だけで公開完了です。

## ソースレイアウト

書くのはこれ一度だけ：

```
my-toolkit/
├── agentpack.yaml           # 名前、バージョン、説明、作者、ターゲット
├── skills/
│   └── review-pr/
│       ├── SKILL.md         # YAML frontmatter + Markdown 指示
│       └── references/…     # 任意の追加ファイル（そのままコピー）
├── commands/                # 任意のスラッシュコマンド（.md）
├── agents/                  # 任意の Claude Code サブエージェント（.md）
├── hooks/hooks.json         # 任意の Claude Code フック（パススルー）
└── .mcp.json                # 任意の MCP サーバー設定（パススルー）
```

### agentpack.yaml

```yaml
name: my-toolkit            # kebab-case、必須
version: 1.0.0              # semver
description: このプラグインが何をするか、エージェントがいつ使うべきか。
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
name: review-pr            # フォルダ名と一致させる必要あり
description: プルリクエストや diff のレビューを求められたときに使用。
paths: "**/*.py"           # 任意；Cursor スタイルのファイルスコープ
---

# エージェントへの指示……
```

## コマンド

| コマンド | 説明 |
| --- | --- |
| `agentpack init [dir]` | 新しいプロジェクトの雛形を作成 |
| `agentpack validate [dir]` | 設定とスキルを検証；エラー時は終了コード 1 |
| `agentpack build [dir]` | `dist/<target>/` バンドルを生成 |
| `agentpack build -t cursor,claude` | 指定ターゲットのみビルド |
| `agentpack targets` | 対応プラットフォームを一覧表示 |

## プラットフォーム差異の扱い

| 概念 | claude | cursor | codex | copilot | agents |
| --- | --- | --- | --- | --- | --- |
| スキル | プラグイン内 `skills/` | `.cursor/skills/` | `.codex/skills/` | `.github/skills/` | `.agents/skills/` |
| スラッシュコマンド | `commands/*.md` | 手動スキルに変換 | 変換 | 変換 | 変換 |
| `paths` / `globs` スコープ | 削除（非対応） | 保持（`globs`→`paths`） | 削除 | 削除 | 保持 |
| サブエージェント（`agents/`） | 出力 | スキップ | スキップ | スキップ | スキップ |
| フック / MCP 設定 | 出力 | スキップ | スキップ | スキップ | スキップ |
| マニフェスト | `plugin.json` + `marketplace.json` | — | — | — | — |

削除・変換されたものはすべてビルド時に `note:` として表示されます。暗黙の挙動はありません。

## サンプル

完全に動作するサンプルは [`examples/code-review-toolkit/`](examples/code-review-toolkit/) にあります：

```bash
agentpack build examples/code-review-toolkit
```

## 開発

```bash
python -m unittest discover tests -v
```

テストにも依存パッケージは不要です。

## ライセンス

MIT
