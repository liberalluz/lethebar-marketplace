# Specs

The site has one job: turn the registry's `index.json` into pages, and leave
every download to the author's release. Its controlled specs are added with the
first release batch (`SRS`, `SDD`, `STP`, `STD`, each with a Chinese page in
`controlled/`).

The build runs in GitHub Actions: `.github/workflows/deploy.yml` checks the
registry out at the full commit named in `REGISTRY_REF`, builds `site/dist`,
uploads it as the Pages artifact, and a verify job compares the sha256 of the
served index with the one the build named.

Until then the upstream contract is the registry's:

- `lethebar-marketplace-registry/docs/specs/controlled/SRS.md` — what a record promises;
- `.../SDD.md` — the index model and the validator;
- `lethebar-marketplace-registry/schema/index.schema.json` — the record shape this build reads.
