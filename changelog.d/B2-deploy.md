# B2 - The site deploys from CI

### Added

- A `deploy` workflow builds the site from the registry commit pinned in
  `REGISTRY_REF`, publishes `site/dist` to GitHub Pages, and fails when the
  served index is not the built one.

### Changed

- The READMEs link the live URL and describe the pipeline instead of a local
  build.

## present

- `changelog.d/B2-deploy.md` — Added the deploy workflow and the served-bytes check.
