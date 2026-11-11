#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check that tags, manifests, and changelogs agree.

Usage:
    python infra/tool/release/check_versions.py --root .
    python infra/tool/release/check_versions.py --root . --strict
    python infra/tool/release/check_versions.py --root . --tags repo/v0.3.0,pack/cultivation/v0.6.0

A stream is `repo` (the repository itself) or a package id. The changelog for a
stream is resolved the same way release.py resolves it: `repo` uses the root
CHANGELOG.md; a package uses its own CHANGELOG.md when the package directory
has one, otherwise the root file may still hold a `## <id> vX.Y.Z` section.

Exit codes: 0 clean, 1 errors (or warnings with --strict), 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

TOOL_VERSION = "0.2.0"

CHANGELOG = "CHANGELOG.md"
PACK_ROOTS = ("packs", "packages", "crates", "modules")
MANIFESTS = ("manifest.json", "package.json", "Cargo.toml", "pyproject.toml")
VERSION = r"v?\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?"
TAG_RE = re.compile(rf"^(?:repo|pack/(?P<pack>[a-z0-9][a-z0-9-]*))/v(?P<version>\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?)$")
SECTION_RE = re.compile(
    rf"^##\s+(?:(?P<stream>[a-z0-9][a-z0-9-]*)\s+)?(?P<version>{VERSION})\s+-\s+(?P<date>\d{{4}}-\d{{2}}-\d{{2}})\s*$"
)
TOML_VERSION_RE = re.compile(r'^version\s*=\s*"([^"]+)"', re.MULTILINE)


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def normalize(version: str) -> str:
    return version[1:] if version.startswith("v") else version


def manifest_version(directory: Path) -> str | None:
    """Return the version a package directory declares, or None."""
    for name in ("manifest.json", "package.json"):
        path = directory / name
        if not path.is_file():
            continue
        try:
            data = json.loads(read_text(path))
        except ValueError:
            continue
        if isinstance(data, dict):
            value = data.get("version")
            if isinstance(value, str) and value.strip():
                return normalize(value.strip())
    for name in ("Cargo.toml", "pyproject.toml"):
        path = directory / name
        if not path.is_file():
            continue
        match = TOML_VERSION_RE.search(read_text(path))
        if match:
            return normalize(match.group(1).strip())
    return None


def detect_packs_root(root: Path) -> Path | None:
    for name in PACK_ROOTS:
        candidate = root / name
        if candidate.is_dir():
            return candidate
    return None


def package_dirs(root: Path, packs_root: Path | None = None) -> dict[str, Path]:
    packs = packs_root or detect_packs_root(root)
    if packs is None or not packs.is_dir():
        return {}
    found: dict[str, Path] = {}
    for directory in sorted(packs.iterdir()):
        if directory.is_dir() and manifest_version(directory) is not None:
            found[directory.name] = directory
    return found


def changelog_sections(path: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """Return (bare versions, (stream, version) pairs) from a changelog file."""
    bare: list[str] = []
    named: list[tuple[str, str]] = []
    for line in read_text(path).splitlines():
        match = SECTION_RE.match(line.strip())
        if not match:
            continue
        version = normalize(match.group("version"))
        stream = match.group("stream")
        if stream:
            named.append((stream, version))
        else:
            bare.append(version)
    return bare, named


def read_tags(root: Path, override: str) -> list[str]:
    if override:
        return [tag.strip() for tag in override.split(",") if tag.strip()]
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "tag", "-l"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise SystemExit(f"check_versions: cannot run git: {exc}")
    if result.returncode != 0:
        raise SystemExit(f"check_versions: git tag failed: {result.stderr.strip()}")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def check(
    root: Path, tags: list[str], packs_root: Path | None = None
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    root_changelog = root / CHANGELOG
    if not root_changelog.is_file():
        errors.append(f"{CHANGELOG}: missing")
        return errors, warnings
    bare, named = changelog_sections(root_changelog)
    streamed: dict[str, list[str]] = {}
    for stream, version in named:
        streamed.setdefault(stream, []).append(version)
    duplicates = sorted({version for version in bare if bare.count(version) > 1})
    for version in duplicates:
        errors.append(f"{CHANGELOG}: version v{version} appears more than once")

    packages = package_dirs(root, packs_root)
    seen_repo = False
    for tag in tags:
        match = TAG_RE.match(tag)
        if not match:
            warnings.append(f"tag {tag}: not a release tag, skipped")
            continue
        version = normalize(match.group("version"))
        pack = match.group("pack")
        if pack is None:
            seen_repo = True
            if version not in bare:
                errors.append(f"{CHANGELOG}: no section for {tag}")
            continue
        directory = packages.get(pack)
        if directory is None:
            errors.append(f"tag {tag}: no package manifest for {pack!r}")
            continue
        declared = manifest_version(directory)
        if declared != version:
            errors.append(
                f"tag {tag}: manifest declares {declared or 'nothing'}, tag says {version}"
            )
        pack_changelog = directory / CHANGELOG
        if pack_changelog.is_file():
            versions, _ = changelog_sections(pack_changelog)
            if version not in versions:
                errors.append(f"tag {tag}: no section in {pack_changelog.relative_to(root)}")
        elif version not in streamed.get(pack, []):
            errors.append(f"tag {tag}: no section in {CHANGELOG} or {pack}/{CHANGELOG}")

    for pack, directory in packages.items():
        if not (directory / CHANGELOG).is_file() and pack not in streamed:
            warnings.append(
                f"{pack}: no {CHANGELOG} and no '## {pack} vX.Y.Z' section "
                f"(run release.py --stream {pack} --write)"
            )
        declared = manifest_version(directory)
        if declared and not any(
            TAG_RE.match(tag) and normalize(TAG_RE.match(tag).group("version")) == declared
            and TAG_RE.match(tag).group("pack") == pack
            for tag in tags
        ):
            warnings.append(f"{pack}: manifest version {declared} has no tag")

    if not seen_repo:
        warnings.append("no repo tag found")
    return errors, warnings


def section_dates(path: Path, default_stream: str = "repo") -> dict[tuple[str, str], str]:
    """Return (stream, version) -> date for every section in a changelog file."""
    dates: dict[tuple[str, str], str] = {}
    for line in read_text(path).splitlines():
        match = SECTION_RE.match(line.strip())
        if not match:
            continue
        stream = match.group("stream") or default_stream
        dates[(stream, normalize(match.group("version")))] = match.group("date")
    return dates


def version_key(version: str) -> tuple:
    """Sort versions numerically; a prerelease sorts before its release."""
    head, _, tail = version.partition("-")
    numbers = tuple(int(part) if part.isdigit() else 0 for part in head.split("."))
    return numbers, 0 if tail else 1, tail


def index_rows(
    root: Path, tags: list[str], packs_root: Path | None = None
) -> list[tuple[str, str, str, str, str]]:
    """Return (stream, version, date, tag, changelog) rows, latest version each."""
    packages = package_dirs(root, packs_root)
    root_changelog = root / CHANGELOG
    dates: dict[tuple[str, str], str] = {}
    if root_changelog.is_file():
        dates.update(section_dates(root_changelog, "repo"))

    versions: dict[str, list[str]] = {}
    for tag in tags:
        match = TAG_RE.match(tag)
        if not match:
            continue
        stream = match.group("pack") or "repo"
        versions.setdefault(stream, []).append(normalize(match.group("version")))

    rows: list[tuple[str, str, str, str, str]] = []
    for stream in sorted(versions, key=lambda name: (name != "repo", name)):
        latest = max(versions[stream], key=version_key)
        changelog = CHANGELOG
        if stream != "repo":
            directory = packages.get(stream)
            if directory is not None and (directory / CHANGELOG).is_file():
                changelog = (directory / CHANGELOG).relative_to(root).as_posix()
                dates.update(section_dates(directory / CHANGELOG, stream))
        tag = f"repo/v{latest}" if stream == "repo" else f"pack/{stream}/v{latest}"
        rows.append((stream, latest, dates.get((stream, latest), "-"), tag, changelog))
    return rows


def render_index(rows: list[tuple[str, str, str, str, str]]) -> str:
    lines = [
        "<!-- generated by check_versions.py --write-index; edit by hand at your own risk -->",
        "",
        "| Stream | Version | Date | Tag | Changelog |",
        "| --- | --- | --- | --- | --- |",
    ]
    for stream, version, date, tag, changelog in rows:
        lines.append(f"| {stream} | v{version} | {date} | {tag} | {changelog} |")
    return "\n".join(lines) + "\n"


def write_index(path: Path, rows: list[tuple[str, str, str, str, str]]) -> bool:
    """Write the index; return True when the file changed."""
    text = render_index(rows)
    if path.is_file() and read_text(path) == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="check tags, manifests, and changelogs agree")
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--packs-root", type=Path)
    parser.add_argument("--tags", default="", help="comma separated tags (default: git tag -l)")
    parser.add_argument("--strict", action="store_true", help="treat every warning as a failure")
    parser.add_argument(
        "--write-index",
        type=Path,
        metavar="PATH",
        help="write a generated table of streams, versions, and changelogs",
    )
    parser.add_argument("--tool-version", action="store_true")
    args = parser.parse_args(argv)

    if args.tool_version:
        print(TOOL_VERSION)
        return 0

    root = args.root.resolve()
    if not root.is_dir():
        print(f"check_versions: not a directory: {root}", file=sys.stderr)
        return 2
    try:
        tags = read_tags(root, args.tags)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2

    errors, warnings = check(root, tags, args.packs_root)
    for warning in warnings:
        print(f"warn  {warning}")
    for error in errors:
        print(f"error {error}")
    if args.write_index:
        rows = index_rows(root, tags, args.packs_root)
        changed = write_index(args.write_index, rows)
        state = "wrote" if changed else "up to date:"
        print(f"{state} {args.write_index}".rstrip())
    print(f"versions: {len(tags)} tag(s), {len(errors)} error(s), {len(warnings)} warning(s)")
    if errors or (args.strict and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
