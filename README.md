# Lethebar marketplace

English · [简体中文](README.zh-CN.md)

The site that lists what the `lethebar-marketplace-registry` index holds: a list
grouped by collection, one page per package version, and a download link that
points at the author's release.

This repository never stores a package. There is no upload, no zip, and no proxy:
every download leaves for the release the author already published.

## Live

The site is at <https://liberalluz.github.io/lethebar-marketplace/>. A push to
`main` builds it from the registry commit named in `.github/workflows/deploy.yml`
(`REGISTRY_REF`), deploys `site/dist` to Pages, and fails when the bytes served
are not the bytes built.

## Build

```text
npm --prefix site install
REGISTRY_DIR=../lethebar-marketplace-registry npm --prefix site run build
```

The build reads `<REGISTRY_DIR>/index.json` and writes `site/dist/`. The checkout
is the pin: the same commit produces the same pages.

## Layout

| Path | Holds |
|---|---|
| `site/` | the build: TypeScript, no framework, no server |
| `infra/` | the Nebula batch runner and the web stack |
| `docs/` | this repository's specs and decisions |

## Docs

- the registry contract: `lethebar-marketplace-registry/docs/specs/controlled/`
- the engine and the pack guide: `lethebar/docs/guide/`
- this repository's plan and records: `lethebar-marketplace-docs`

## Licence

Apache-2.0. See `LICENSE`.
