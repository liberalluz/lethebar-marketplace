# Lethebar 市场

[English](README.md) · 简体中文

`lethebar-marketplace-registry` 索引的展示站：按 collection 分组的列表、每个包版本一页、
下载链接指向作者自己的 Release。

这个仓不存包。没有上传、没有 zip、没有代理：每次下载都离开本站，去作者已经发布的 Release。

## 构建

```text
npm --prefix site install
REGISTRY_DIR=../lethebar-marketplace-registry npm --prefix site run build
```

构建读 `<REGISTRY_DIR>/index.json`，写 `site/dist/`。检出就是钉住的版本：同一个提交产出同一批页面。

## 目录

| 路径 | 放什么 |
|---|---|
| `site/` | 构建：TypeScript，无框架，无服务器 |
| `infra/` | Nebula 批次工具与 web 技术栈 |
| `docs/` | 这个仓的规格与决定 |

## 文档

- registry 契约：`lethebar-marketplace-registry/docs/specs/controlled/`
- 引擎与写包指南：`lethebar/docs/guide/`
- 这个仓的计划与记录：`lethebar-marketplace-docs`

## 许可

Apache-2.0，见 `LICENSE`。
