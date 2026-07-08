"""A tiny, dependency-free parser/dumper for the YAML subset used by
agentpack.yaml and SKILL.md frontmatter.

Supported syntax:
  - key: value mappings (nested via indentation)
  - block lists (``- item``), including lists of mappings
  - inline lists (``[a, b, c]``)
  - quoted and plain scalars, booleans, null, ints, floats
  - full-line and trailing comments

Not supported (by design): anchors, aliases, multi-document streams,
block scalars (| and >), flow mappings. If a project needs those, the
config is more complicated than it should be.
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple


class MiniYamlError(ValueError):
    def __init__(self, message: str, line_no: Optional[int] = None):
        self.line_no = line_no
        if line_no is not None:
            message = f"line {line_no}: {message}"
        super().__init__(message)


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

def _strip_comment(text: str) -> str:
    """Remove a trailing comment that is not inside quotes."""
    in_single = in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if i == 0 or text[i - 1] in " \t":
                return text[:i]
    return text


def _parse_scalar(token: str, line_no: int) -> Any:
    token = token.strip()
    if token == "":
        return None
    if token.startswith('"') and token.endswith('"') and len(token) >= 2:
        return token[1:-1].replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
    if token.startswith("'") and token.endswith("'") and len(token) >= 2:
        return token[1:-1].replace("''", "'")
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_parse_scalar(part, line_no) for part in _split_inline_list(inner, line_no)]
    lowered = token.lower()
    if lowered in ("true", "yes", "on"):
        return True
    if lowered in ("false", "no", "off"):
        return False
    if lowered in ("null", "~", "none"):
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _split_inline_list(inner: str, line_no: int) -> List[str]:
    parts: List[str] = []
    current = ""
    in_single = in_double = False
    depth = 0
    for ch in inner:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "[" and not in_single and not in_double:
            depth += 1
        elif ch == "]" and not in_single and not in_double:
            depth -= 1
        if ch == "," and not in_single and not in_double and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    if in_single or in_double:
        raise MiniYamlError("unterminated quote in inline list", line_no)
    return parts


def _split_key_value(text: str, line_no: int) -> Optional[Tuple[str, str]]:
    """Split ``key: value`` respecting quotes. Returns None if no key found."""
    in_single = in_double = False
    for i, ch in enumerate(text):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == ":" and not in_single and not in_double:
            if i + 1 >= len(text) or text[i + 1] in " \t" or i + 1 == len(text.rstrip()):
                key = text[:i].strip()
                if key.startswith(('"', "'")):
                    key = _parse_scalar(key, line_no)
                return key, text[i + 1:].strip()
    return None


class _Line:
    __slots__ = ("indent", "content", "no")

    def __init__(self, indent: int, content: str, no: int):
        self.indent = indent
        self.content = content
        self.no = no


def _tokenize(text: str) -> List[_Line]:
    lines: List[_Line] = []
    for no, raw in enumerate(text.splitlines(), start=1):
        if "\t" in raw[: len(raw) - len(raw.lstrip())]:
            raise MiniYamlError("tabs are not allowed for indentation", no)
        stripped = _strip_comment(raw).rstrip()
        if not stripped.strip():
            continue
        indent = len(stripped) - len(stripped.lstrip())
        lines.append(_Line(indent, stripped.strip(), no))
    return lines


def _parse_block(lines: List[_Line], pos: int, indent: int) -> Tuple[Any, int]:
    if pos >= len(lines):
        return None, pos
    if lines[pos].content.startswith("- "):
        return _parse_list(lines, pos, indent)
    return _parse_map(lines, pos, indent)


def _parse_list(lines: List[_Line], pos: int, indent: int) -> Tuple[List[Any], int]:
    result: List[Any] = []
    while pos < len(lines) and lines[pos].indent == indent and lines[pos].content.startswith("- "):
        line = lines[pos]
        rest = line.content[2:].strip()
        kv = _split_key_value(rest, line.no) if rest else None
        if kv is not None:
            # list item is a mapping; treat "- key: value" as its first entry
            item: dict = {}
            key, value = kv
            if value == "":
                child, pos = _parse_block(lines, pos + 1, _next_indent(lines, pos, indent + 2))
                item[key] = child
            else:
                item[key] = _parse_scalar(value, line.no)
                pos += 1
            while pos < len(lines) and lines[pos].indent == indent + 2 and not lines[pos].content.startswith("- "):
                sub = _split_key_value(lines[pos].content, lines[pos].no)
                if sub is None:
                    raise MiniYamlError("expected 'key: value'", lines[pos].no)
                skey, svalue = sub
                if svalue == "":
                    child, pos = _parse_block(lines, pos + 1, _next_indent(lines, pos, indent + 4))
                    item[skey] = child
                else:
                    item[skey] = _parse_scalar(svalue, lines[pos].no)
                    pos += 1
            result.append(item)
        elif rest:
            result.append(_parse_scalar(rest, line.no))
            pos += 1
        else:
            child, pos = _parse_block(lines, pos + 1, _next_indent(lines, pos, indent + 2))
            result.append(child)
    return result, pos


def _next_indent(lines: List[_Line], pos: int, fallback: int) -> int:
    if pos + 1 < len(lines):
        return lines[pos + 1].indent
    return fallback


def _parse_map(lines: List[_Line], pos: int, indent: int) -> Tuple[dict, int]:
    result: dict = {}
    while pos < len(lines) and lines[pos].indent == indent:
        line = lines[pos]
        if line.content.startswith("- "):
            break
        kv = _split_key_value(line.content, line.no)
        if kv is None:
            raise MiniYamlError(f"expected 'key: value', got {line.content!r}", line.no)
        key, value = kv
        if key in result:
            raise MiniYamlError(f"duplicate key {key!r}", line.no)
        if value == "":
            if pos + 1 < len(lines) and lines[pos + 1].indent > indent:
                child, pos = _parse_block(lines, pos + 1, lines[pos + 1].indent)
                result[key] = child
            else:
                result[key] = None
                pos += 1
        else:
            result[key] = _parse_scalar(value, line.no)
            pos += 1
    return result, pos


def loads(text: str) -> Any:
    """Parse a YAML-subset document. Returns a dict, list or scalar."""
    lines = _tokenize(text)
    if not lines:
        return {}
    value, pos = _parse_block(lines, 0, lines[0].indent)
    if pos < len(lines):
        raise MiniYamlError(
            f"unexpected content (check indentation): {lines[pos].content!r}", lines[pos].no
        )
    return value


# ---------------------------------------------------------------------------
# Dumping (used to emit SKILL.md frontmatter and config scaffolds)
# ---------------------------------------------------------------------------

_PLAIN_SAFE = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_./ @()+")


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value)
    needs_quotes = (
        text == ""
        or text.strip() != text
        or any(ch not in _PLAIN_SAFE for ch in text)
        or text.lower() in ("true", "false", "yes", "no", "on", "off", "null", "~", "none")
        or text[0] in "-?:#&*!|>%@`\"'[]{}"
    )
    if needs_quotes:
        escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
        return f'"{escaped}"'
    return text


def _dump_node(value: Any, indent: int, out: List[str]) -> None:
    pad = " " * indent
    if isinstance(value, dict):
        for key, val in value.items():
            if isinstance(val, (dict, list)) and val:
                out.append(f"{pad}{key}:")
                _dump_node(val, indent + 2, out)
            elif isinstance(val, (dict, list)):
                out.append(f"{pad}{key}: " + ("{}" if isinstance(val, dict) else "[]"))
            else:
                out.append(f"{pad}{key}: {_dump_scalar(val)}")
    elif isinstance(value, list):
        for item in value:
            if isinstance(item, dict) and item:
                keys = list(item.keys())
                first = keys[0]
                fval = item[first]
                if isinstance(fval, (dict, list)) and fval:
                    out.append(f"{pad}- {first}:")
                    _dump_node(fval, indent + 4, out)
                else:
                    out.append(f"{pad}- {first}: {_dump_scalar(fval)}")
                for key in keys[1:]:
                    val = item[key]
                    if isinstance(val, (dict, list)) and val:
                        out.append(f"{pad}  {key}:")
                        _dump_node(val, indent + 4, out)
                    else:
                        out.append(f"{pad}  {key}: {_dump_scalar(val)}")
            elif isinstance(item, list):
                inline = ", ".join(_dump_scalar(x) for x in item)
                out.append(f"{pad}- [{inline}]")
            else:
                out.append(f"{pad}- {_dump_scalar(item)}")
    else:
        out.append(f"{pad}{_dump_scalar(value)}")


def dumps(value: Any) -> str:
    out: List[str] = []
    _dump_node(value, 0, out)
    return "\n".join(out) + "\n"
