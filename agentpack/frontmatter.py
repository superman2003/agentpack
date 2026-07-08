"""Read and write Markdown files with YAML frontmatter."""

from __future__ import annotations

from typing import Any, Dict, Tuple

from . import miniyaml


class FrontmatterError(ValueError):
    pass


def split(text: str) -> Tuple[Dict[str, Any], str]:
    """Split a Markdown document into (frontmatter dict, body).

    A document without frontmatter returns ({}, full text).
    """
    if not text.startswith("---"):
        return {}, text
    first_line_end = text.find("\n")
    if first_line_end == -1 or text[:first_line_end].strip() != "---":
        return {}, text
    rest = text[first_line_end + 1:]
    for candidate in ("\n---\n", "\n---\r\n", "\r\n---\r\n", "\r\n---\n"):
        idx = rest.find(candidate)
        if idx != -1:
            fm_text = rest[:idx]
            body = rest[idx + len(candidate):]
            break
    else:
        # frontmatter closes at EOF
        stripped = rest.rstrip()
        if stripped.endswith("\n---") or stripped == "---":
            fm_text = stripped[: -3].rstrip()
            body = ""
        else:
            raise FrontmatterError("frontmatter opened with '---' but never closed")
    try:
        data = miniyaml.loads(fm_text)
    except miniyaml.MiniYamlError as exc:
        raise FrontmatterError(f"invalid frontmatter: {exc}") from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise FrontmatterError("frontmatter must be a mapping")
    return data, body


def join(data: Dict[str, Any], body: str) -> str:
    """Render frontmatter + body back into a Markdown document."""
    if not data:
        return body
    fm = miniyaml.dumps(data)
    body = body.lstrip("\n")
    return f"---\n{fm}---\n\n{body}"
