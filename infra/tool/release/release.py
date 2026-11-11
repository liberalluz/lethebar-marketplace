#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compose a release section from changelog.d fragments.

Usage:
    python infra/tool/release/release.py --root . --check
    python infra/tool/release/release.py --root . --render --version v1.2.3
    python infra/tool/release/release.py --root . --write --version v1.2.3
    python infra/tool/release/release.py --root . --write --stream cultivation --version v0.6.0

`--write` updates the target changelog and removes only the fragments it
consumed. `--render` prints the section without changing anything. Default is
`--check`. `--stream` selects `repo` (default) or a package id; a package writes
its own CHANGELOG.md when the package directory has a manifest, otherwise the
root file keeps a `## <id> vX.Y.Z` section.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

TOOL_VERSION = "0.2.0"

ROOT = Path(__file__).resolve().parents[3]
CHANGELOG = "CHANGELOG.md"
FRAGMENT_DIR = "changelog.d"
FRAGMENT_README = "README.md"
SECTIONS = ("Added", "Changed", "Fixed", "Removed")
PACK_ROOTS = ("packs", "packages", "crates", "modules")
MANIFESTS = ("manifest.json", "package.json", "Cargo.toml", "pyproject.toml")
STREAM_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
VERSION_RE = re.compile(r"^v(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)(?:-[0-9A-Za-z.-]+)?$")
DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")
SECTION_RE = re.compile(r"^### (Added|Changed|Fixed|Removed)\s*$")
H2_RE = re.compile(r"^##\s")


class ReleaseError(Exception):
    """A user-facing release input error."""


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ReleaseError(f"cannot read {path}: {exc}") from exc


def parse_fragment(path: Path) -> dict[str, list[str]]:
    text = read_text(path)
    if not text.strip():
        raise ReleaseError(f"{path.name}: empty fragment")
    if text.lstrip().startswith("---"):
        raise ReleaseError(f"{path.name}: front matter is not allowed")

    result = {section: [] for section in SECTIONS}
    seen: set[str] = set()
    current: str | None = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.startswith("# "):
            raise ReleaseError(f"{path.name}: H1 is not allowed in a fragment")
        if line.startswith("## "):
            raise ReleaseError(f"{path.name}: H2 is not allowed in a fragment")
        match = SECTION_RE.match(line)
        if match:
            current = match.group(1)
            if current in seen:
                raise ReleaseError(f"{path.name}: duplicate ### {current}")
            seen.add(current)
            continue
        if line.startswith("### "):
            raise ReleaseError(
                f"{path.name}: only ### Added/Changed/Fixed/Removed are allowed"
            )
        stripped = line.lstrip()
        if stripped.startswith("- "):
            if current is None:
                raise ReleaseError(f"{path.name}: bullet outside a section")
            item = stripped[2:].strip()
            if not item:
                raise ReleaseError(f"{path.name}: empty bullet")
            result[current].append(item)
            continue
        if line.startswith((" ", "\t")):
            if current is None or not result[current]:
                raise ReleaseError(f"{path.name}: continuation without a bullet")
            result[current][-1] += " " + line.strip()
            continue
        raise ReleaseError(f"{path.name}: content outside a section")

    if not any(result.values()):
        raise ReleaseError(f"{path.name}: no release notes")
    return result


def has_manifest(directory: Path) -> bool:
    return directory.is_dir() and any(
        (directory / name).is_file() for name in MANIFESTS
    )


def detect_packs_root(root: Path) -> Path | None:
    for name in PACK_ROOTS:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


def resolve_target(
    root: Path,
    stream: str,
    packs_root: Path | None = None,
    changelog: Path | None = None,
) -> tuple[Path, str]:
    """Return the changelog file for a stream and its heading prefix.

    An empty prefix means the file holds one stream: the root file for `repo`,
    or a package file under the packs root. A non-empty prefix means the
    stream shares the root file, e.g. `## cultivation v0.6.0 - 2026-11-10`.
    """
    if changelog is not None:
        path = changelog if changelog.is_absolute() else root / changelog
        return path, ""
    if stream == "repo":
        return root / CHANGELOG, ""
    packs = packs_root or detect_packs_root(root)
    if packs is not None:
        directory = packs / stream
        if has_manifest(directory) or (directory / CHANGELOG).is_file():
            return directory / CHANGELOG, ""
    return root / CHANGELOG, f"{stream} "


def fragment_dir(root: Path, stream: str) -> Path:
    nested = root / FRAGMENT_DIR / stream
    if nested.is_dir():
        return nested
    if stream == "repo":
        return root / FRAGMENT_DIR
    raise ReleaseError(
        f"{FRAGMENT_DIR}/{stream}/ is missing; put fragments for {stream!r} there"
    )


def collect(
    root: Path, stream: str = "repo"
) -> tuple[dict[str, list[str]], list[Path]]:
    directory = fragment_dir(root, stream)
    if not directory.is_dir():
        raise ReleaseError(f"{FRAGMENT_DIR}/ is missing")
    paths = sorted(
        path
        for path in directory.glob("*.md")
        if path.is_file() and path.name != FRAGMENT_README
    )
    if not paths:
        raise ReleaseError(f"{directory.relative_to(root)} has no fragments")

    merged = {section: [] for section in SECTIONS}
    for path in paths:
        parsed = parse_fragment(path)
        for section in SECTIONS:
            merged[section].extend(parsed[section])
    return merged, paths


def validate_version(version: str) -> None:
    if not VERSION_RE.match(version):
        raise ReleaseError(f"version must look like v1.2.3, got {version!r}")


def validate_date(value: str) -> None:
    if not DATE_RE.match(value):
        raise ReleaseError(f"date must be YYYY-MM-DD, got {value!r}")
    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ReleaseError(f"invalid date: {value!r}") from exc


def compose(
    notes: dict[str, list[str]], version: str, day: str, prefix: str = ""
) -> str:
    validate_version(version)
    validate_date(day)
    lines = [f"## {prefix}{version} - {day}", ""]
    for section in SECTIONS:
        if not notes[section]:
            continue
        lines.append(f"### {section}")
        lines.extend(f"- {item}" for item in notes[section])
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _strip_empty_unreleased(lines: list[str]) -> list[str]:
    index = next(
        (i for i, line in enumerate(lines) if line.strip() == "## Unreleased"),
        None,
    )
    if index is None:
        return lines
    end = next(
        (i for i in range(index + 1, len(lines)) if H2_RE.match(lines[i])),
        len(lines),
    )
    content = [
        line
        for line in lines[index + 1 : end]
        if line.strip() and not SECTION_RE.match(line)
    ]
    if content:
        raise ReleaseError(
            "CHANGELOG.md has content under ## Unreleased; "
            "move it into changelog.d/ before releasing"
        )
    return lines[:index] + lines[end:]


def insert_version(text: str, section: str, version: str, prefix: str = "") -> str:
    lines = text.splitlines()
    if lines and lines[0].strip() != "# Changelog":
        raise ReleaseError("CHANGELOG.md must start with '# Changelog'")
    if any(line.strip().startswith(f"## {prefix}{version}") for line in lines):
        raise ReleaseError(f"changelog already has {prefix}{version}")
    lines = _strip_empty_unreleased(lines)

    index = next((i for i, line in enumerate(lines) if H2_RE.match(line)), None)
    block = section.rstrip("\n").splitlines()
    if index is None:
        if lines and lines[-1].strip():
            lines.append("")
        lines.extend(block)
    else:
        if index and lines[index - 1].strip():
            block = ["", *block]
        lines[index:index] = [*block, ""]
    return "\n".join(lines).rstrip() + "\n"


def write_release(
    root: Path,
    version: str,
    day: str,
    *,
    stream: str = "repo",
    packs_root: Path | None = None,
    changelog: Path | None = None,
) -> tuple[Path, int]:
    notes, paths = collect(root, stream)
    validate_version(version)
    validate_date(day)
    target, prefix = resolve_target(root, stream, packs_root, changelog)
    section = compose(notes, version, day, prefix)

    if target.is_file():
        text = read_text(target)
    else:
        text = "# Changelog\n"
    updated = insert_version(text, section, version, prefix)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(updated, encoding="utf-8", newline="\n")
    for path in paths:
        path.unlink()
    return target, len(paths)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="compose release notes from changelog.d")
    parser.add_argument("--root", type=Path, default=Path("."))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true")
    group.add_argument("--render", action="store_true")
    group.add_argument("--write", action="store_true")
    parser.add_argument("--version", default="")
    parser.add_argument(
        "--stream",
        default="repo",
        help="repo, or a package id that owns its own changelog (default: repo)",
    )
    parser.add_argument(
        "--packs-root",
        type=Path,
        help="directory holding package manifests (default: packs, packages, crates, modules)",
    )
    parser.add_argument(
        "--changelog",
        type=Path,
        help="write to this file instead of resolving one from the stream",
    )
    parser.add_argument("--tool-version", action="store_true", help="print the tool version and exit")
    parser.add_argument("--date", default=date.today().isoformat())
    args = parser.parse_args(argv)

    if args.tool_version:
        print(TOOL_VERSION)
        return 0

    stream = args.stream.strip()
    if not STREAM_RE.match(stream):
        print(f"release: invalid stream {stream!r}", file=sys.stderr)
        return 2
    root = args.root.resolve()
    try:
        target, prefix = resolve_target(
            root, stream, args.packs_root, args.changelog
        )
        if args.write or args.render:
            if not args.version:
                raise ReleaseError("--version is required with --render/--write")
            validate_version(args.version)
            validate_date(args.date)
            notes, _ = collect(root, stream)
            section = compose(notes, args.version, args.date, prefix)
            if args.render:
                sys.stdout.write(section)
                return 0
            target, count = write_release(
                root,
                args.version,
                args.date,
                stream=stream,
                packs_root=args.packs_root,
                changelog=args.changelog,
            )
            print(
                f"release: wrote {target.relative_to(root).as_posix()} "
                f"and removed {count} fragment(s)"
            )
            return 0

        notes, paths = collect(root, stream)
        if args.version:
            validate_version(args.version)
            text = read_text(target) if target.is_file() else ""
            if any(line.strip().startswith(f"## {prefix}{args.version}") for line in text.splitlines()):
                raise ReleaseError(f"changelog already has {prefix}{args.version}")
        total = sum(len(items) for items in notes.values())
        print(f"release: {len(paths)} fragment(s), {total} note(s), all valid")
        return 0
    except ReleaseError as exc:
        print(f"release: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
