# 静态站点（TypeScript）

一个构建静态站点的组件：TypeScript 源码，没有服务器，没有框架。构建读输入，写
`site/dist/`。

```text
--component site=web
```

- 源码在 `site/`。`npm --prefix site run build` 写 `dist/`。
- 只有 bootstrap 带 `--accept-stack web` 时，这个栈才贡献五条检查
  （`format`、`lint`、`typecheck`、`build`、`test`）。
- `node_modules/` 与 `dist/` 是生成物，不提交。

组件有代码、有构建时用它，不要用 `data`。`data` 不声明语言、不贡献命令，会把站点
描述成“一摞文档”。
