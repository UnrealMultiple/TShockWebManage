#!/usr/bin/env python3
"""Sync TShock schema descriptions from Pryaxis Chinese wiki pages.

Updates descriptions in:
- Web/src/config/tshock_schema.js

Only existing schema keys are updated; keys not present in schema are ignored.
"""

from __future__ import annotations

import argparse
import re
import sys
import urllib.parse
import urllib.request
from pathlib import Path


def _find_repo_root() -> Path:
    cur = Path(__file__).resolve()
    for p in [cur.parent, *cur.parents]:
        candidate = p / "Web" / "src" / "config" / "tshock_schema.js"
        if candidate.exists():
            return p
    raise RuntimeError("repo root not found (missing Web/src/config/tshock_schema.js)")


ROOT = _find_repo_root()
SCHEMA_FILE = ROOT / "Web" / "src" / "config" / "tshock_schema.js"

WIKI_TITLES = {
    "config": "(中文)主配置(config.json)",
    "ssc": "(中文)服务端角色配置(sscconfig.json)",
}


def fetch_wiki_markdown(title: str) -> str:
    encoded = urllib.parse.quote(title)
    candidates = [
        f"https://raw.githubusercontent.com/wiki/Pryaxis/TShock/{encoded}.md",
        f"https://raw.githubusercontent.com/wiki/Pryaxis/TShock/{title}.md",
    ]

    last_err: Exception | None = None
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "schema-sync-script/1.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as exc:  # noqa: BLE001
            last_err = exc

    raise RuntimeError(f"failed to fetch wiki page: {title} ({last_err})")


def parse_wiki_descriptions(md_text: str) -> dict[str, str]:
    """Parse sections like:
    ## FieldName
    Permalink: FieldName
    描述...
    • 字段类型: ...
    """
    lines = md_text.splitlines()
    out: dict[str, str] = {}

    i = 0
    while i < len(lines):
        m = re.match(r"^##\s+(.+?)\s*$", lines[i].strip())
        if not m:
            i += 1
            continue

        key = m.group(1).strip()
        i += 1

        desc_lines: list[str] = []
        while i < len(lines):
            cur = lines[i].strip()
            if cur.startswith("## "):
                break
            if cur.startswith("Permalink:"):
                i += 1
                continue
            if re.match(r"^[•*\-]\s*(字段类型|默认值)\s*:", cur):
                break
            if re.match(r"^[•*\-]\s*(Field\s*Type|Default)\s*:", cur, flags=re.IGNORECASE):
                break
            if cur:
                desc_lines.append(cur)
            i += 1

        desc = re.sub(r"\s+", " ", " ".join(desc_lines)).strip()
        if desc:
            out[key] = desc

    return out


def parse_schema_block(content: str, block_name: str) -> tuple[int, int]:
    marker = f"export const {block_name} = ["
    start = content.find(marker)
    if start < 0:
        raise RuntimeError(f"block not found: {block_name}")

    bracket_start = content.find("[", start)
    if bracket_start < 0:
        raise RuntimeError(f"array start not found: {block_name}")

    depth = 0
    in_string = False
    quote_char = ""
    i = bracket_start
    while i < len(content):
        ch = content[i]
        prev = content[i - 1] if i > 0 else ""

        if in_string:
            if ch == quote_char and prev != "\\":
                in_string = False
        else:
            if ch in ("'", '"'):
                in_string = True
                quote_char = ch
            elif ch == "[":
                depth += 1
            elif ch == "]":
                depth -= 1
                if depth == 0:
                    return bracket_start + 1, i
        i += 1

    raise RuntimeError(f"array end not found: {block_name}")


def js_escape_single_quote(text: str) -> str:
    return text.replace("\\", "\\\\").replace("'", "\\'")


def update_block(block_text: str, desc_map: dict[str, str]) -> tuple[str, int]:
    updated_count = 0

    # Match one schema object at a time, preserving all spacing/style except description value.
    object_pattern = re.compile(
        r"(?P<prefix>\{\s*key:\s*'(?P<key>[^']+)'(?P<body>.*?)description:\s*')(?P<desc>(?:\\'|[^'])*)(?P<suffix>'\s*\},?)",
        flags=re.DOTALL,
    )

    def repl(match: re.Match[str]) -> str:
        nonlocal updated_count
        key = match.group("key")
        old_desc = match.group("desc")
        new_desc_raw = desc_map.get(key)
        if not new_desc_raw:
            return match.group(0)

        new_desc = js_escape_single_quote(new_desc_raw)
        if new_desc == old_desc:
            return match.group(0)

        updated_count += 1
        return f"{match.group('prefix')}{new_desc}{match.group('suffix')}"

    new_block = object_pattern.sub(repl, block_text)
    return new_block, updated_count


def sync_schema(dry_run: bool = False) -> int:
    content = SCHEMA_FILE.read_text(encoding="utf-8")

    config_md = fetch_wiki_markdown(WIKI_TITLES["config"])
    ssc_md = fetch_wiki_markdown(WIKI_TITLES["ssc"])
    config_desc = parse_wiki_descriptions(config_md)
    ssc_desc = parse_wiki_descriptions(ssc_md)

    c_start, c_end = parse_schema_block(content, "CONFIG_SCHEMA")
    s_start, s_end = parse_schema_block(content, "SSC_SCHEMA")

    config_block = content[c_start:c_end]
    ssc_block = content[s_start:s_end]

    new_config_block, c_updated = update_block(config_block, config_desc)
    new_ssc_block, s_updated = update_block(ssc_block, ssc_desc)

    new_content = content
    # Replace later block first to keep indexes valid.
    if s_start > c_start:
        new_content = new_content[:s_start] + new_ssc_block + new_content[s_end:]
        new_content = new_content[:c_start] + new_config_block + new_content[c_end:]
    else:
        new_content = new_content[:c_start] + new_config_block + new_content[c_end:]
        new_content = new_content[:s_start] + new_ssc_block + new_content[s_end:]

    total_updated = c_updated + s_updated
    print(f"CONFIG_SCHEMA updated: {c_updated}")
    print(f"SSC_SCHEMA updated: {s_updated}")
    print(f"Total updated: {total_updated}")

    if total_updated > 0 and not dry_run:
        SCHEMA_FILE.write_text(new_content, encoding="utf-8")
        print(f"Wrote: {SCHEMA_FILE}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync TShock schema descriptions from wiki")
    parser.add_argument("--dry-run", action="store_true", help="Only show update count, do not modify file")
    args = parser.parse_args()

    try:
        return sync_schema(dry_run=args.dry_run)
    except Exception as exc:  # noqa: BLE001
        print(f"[sync_tshock_schema] ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
