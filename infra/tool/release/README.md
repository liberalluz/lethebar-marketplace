# release.py / check_versions.py / publish.py

> 中文：[简体中文](README.zh-CN.md)

Compose a release section from `changelog.d/` fragments, check that tags,
manifests, and changelogs agree, then publish through the provider recorded in
`.nebula-scaffold.json`.

Copied by `nebula-bootstrap --with-release` to `infra/tool/release/`. The tools
are project-local; they are not skills.

## Commands

```bash
python infra/tool/release/release.py --root . --check
python infra/tool/release/release.py --root . --render --version v1.2.3
python infra/tool/release/release.py --root . --write --version v1.2.3

# a package that owns its own CHANGELOG.md
python infra/tool/release/release.py --root . --write --stream cultivation --version v0.6.0

python infra/tool/release/check_versions.py --root .
python infra/tool/release/check_versions.py --root . --strict
python infra/tool/release/check_versions.py --root . --write-index VERSIONS.md

python infra/tool/release/publish.py --root . --version v1.2.3 \
  --docs-root ../<project>-docs --check
python infra/tool/release/publish.py --root . --version v1.2.3 \
  --docs-root ../<project>-docs --apply
```

`--docs-root` is required and must be the sibling `<project>-docs`; the tool
does not guess it.

- `release.py --check` (default) validates every fragment; no files change.
- `release.py --render` prints the `## vX.Y.Z - YYYY-MM-DD` section; no files change.
- `release.py --write` inserts the section into the target changelog, then removes
  the fragments it consumed. It refuses to overwrite an existing version.
- `release.py --stream ID` selects the stream: `repo` (default) or a package id.
  `--packs-root` overrides package discovery; `--changelog` writes to an explicit
  file instead of resolving one.
- `check_versions.py` compares tags (`repo/vX.Y.Z`, `pack/<id>/vX.Y.Z`) with
  manifests and changelog sections; `--strict` turns warnings into failures.
- `check_versions.py --write-index PATH` writes a generated table of streams,
  versions, dates, tags, and changelog paths. It is optional: skip it and keep
  your own index, or re-run it whenever a release lands.
- `publish.py --check` validates provider, annotated tag, body, and evidence path;
  it does not call the provider or require authentication.
- `publish.py --apply` checks provider authentication (`gh auth status` or
  `glab auth status`), creates the provider Release, and writes evidence under
  `records/<YYYY-MM>-release-vX.Y.Z/`. It does not create or push tags.
- `repository` in `release.json` is derived from `origin` (scp or HTTPS), not
  left empty; pass `--repo OWNER/NAME` to override. GitHub/GitLab publish fails
  when the origin has no derivable `OWNER/NAME`.

`release.py --date` defaults to today. `--version` and `--date` are required for
`--render` and `--write`. `publish.py` requires `--version` and `--docs-root`.
Both tools report their own version with `--tool-version`.

## Tool versioning

The release tools are copied once into the project; do not fetch them from the
Nebula checkout on every release. `bootstrap --with-release` writes
`infra/tool/release/.nebula-tool.json` with the tool name, version, per-file
hashes, aggregate `sha256`, and the source commit when available.

Run the project copy on every release. Upgrade the copy separately:

```bash
python <nebula-skills-dev>/skills/nebula-bootstrap/scripts/sync_tools.py \
  --root . --check
python <nebula-skills-dev>/skills/nebula-bootstrap/scripts/sync_tools.py \
  --root . --apply
```

`--check` is read-only. Missing files and hash drift fail it; an available
upgrade is printed as a note and never fails it, even with `--strict`. During an
upgrade window the copy is expected to be behind until you run `--apply`, so
treat `--check` as a release-time step, not a per-batch gate. `--apply` replaces
only `release.py`, `check_versions.py`, `publish.py`, `README.md`, and
`.nebula-tool.json`; it does not touch `CHANGELOG.md`, `changelog.d/`, tags, or
the provider release. Commit the upgrade as its own change, before the release PR.

## Multiple streams

A stream is `repo` (the repository itself) or a package id. The layout is
resolved, never hardcoded:

1. `repo` writes the root `CHANGELOG.md`.
2. A package id writes `<packs-root>/<id>/CHANGELOG.md` when that directory has a
   manifest (`manifest.json`, `package.json`, `Cargo.toml`, or `pyproject.toml`)
   or already has a changelog.
3. Otherwise the package falls back to the root file and keeps its id in the
   heading: `## cultivation v0.6.0 - 2026-11-10`.

The packs root is `--packs-root`, else the first existing directory among
`packs/`, `packages/`, `crates/`, `modules/`. A directory name is a hint, not a
rule: the manifest decides which stream a directory belongs to.

Fragments live in `changelog.d/<stream>/`; `repo` may keep them flat in
`changelog.d/`. A stream with no fragment directory is an error, so a release
cannot silently consume another stream's notes.

`check_versions.py` accepts both layouts: a package file, or the `## <id> vX.Y.Z`
section in the root file. Mixing them passes with a warning until you migrate.

## Fragment format

```markdown
### Added
- new user-visible capability

### Fixed
- wrong state after restart
```

Only `### Added / Changed / Fixed / Removed`, one bullet per note, no H1/H2 or
front matter. `changelog.d/README.md` is never consumed.

## Provider binding

`publish.py` reads `.nebula-scaffold.json.repoPolicy.provider`:

- `github` → `gh release create --verify-tag`
- `gitlab` → `glab release create`
- `none` → local evidence only, no remote call

The tag must already exist locally and be pushed before `--apply`. It must be
an **annotated** tag (`git tag -a v1.2.3 -m "v1.2.3"`); a lightweight tag is
rejected. The tool never creates or pushes tags.

### Release type (GitHub only)

`publish.py --apply` defaults to a normal, non-draft, non-prerelease Release.
For GitHub, pass any of:

- `--draft`
- `--prerelease`
- `--latest`

GitLab rejects these flags. The chosen options are recorded in `release.json`.
Use `--latest` only for a stable release: GitHub's "latest" semantics are not
meant for prereleases, and combining `--latest` with `--prerelease` is allowed
by the CLI but not recommended.

### Failure recovery

Before the remote call, evidence is written with status `pending`. On success it
becomes `created`; on failure it becomes `failed`, and the command exits non-zero.
A pending or failed evidence directory is retryable. Re-run `--apply`: if the
provider already has the Release, the tool marks the evidence `created` without
creating it again; otherwise it retries the remote call. Never delete a `created`
record; if the evidence update failed after a successful remote call, the same
re-run reconciles it.

## Boundaries

- `CHANGELOG.md` is the technical changelog; it is updated only by `release.py`.
- User-facing release notes live outside the repo, under
  `product/release-notes/` in `<project>-docs`; pass them with `--body-file`.
- `publish.py` does not create commits, tags, or push tags.
- Release evidence is `release-notes.md` + `release.json` + `README.md` under
  `records/<YYYY-MM>-release-vX.Y.Z/`; freeze it with `nebula-delivery`.
