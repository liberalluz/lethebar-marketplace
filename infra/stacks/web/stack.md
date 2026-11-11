# Static web (TypeScript)

A component that builds a static site: TypeScript source, no server, no
framework. The build reads its input and writes `site/dist/`.

```text
--component site=web
```

- `site/` holds the source. `npm --prefix site run build` writes `dist/`.
- The stack contributes five checks (`format`, `lint`, `typecheck`, `build`,
  `test`) only when bootstrap is given `--accept-stack web`.
- `node_modules/` and `dist/` are generated: they are not committed.

Use this instead of the `data` stack when the component has code and a build.
`data` declares no language and no commands, which would make a site look like a
folder of documents.
