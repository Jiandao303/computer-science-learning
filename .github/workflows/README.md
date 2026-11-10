# .github/workflows —— 自动部署配置

> ⚠ **当前是占位目录。本轮不创建公开仓库、不部署网站。**
> 这里只放设计说明，实际的 workflow YAML 等工作流确定后再写。

---

## 将来要做什么

两条流水线：

| 文件（计划） | 触发 | 作用 |
| --- | --- | --- |
| `deploy-docs.yml` | push 到 `main`，且改动含 `docs/**` | 构建 VitePress 并发布到 GitHub Pages |
| `check.yml` | PR / push | 链接检查 + frontmatter 校验，失败则阻止合并 |

---

## 为什么现在不写

写 workflow 之前有三件事没定：

1. **仓库地址**：`computer-science-learning` 只是计划名，未创建。
2. **Pages 的发布源**：用 `gh-pages` 分支还是 Actions artifact。
3. **docs 的构建工具**：VitePress 需要 `package.json` + Node 版本，现在 `docs/` 还只是 Markdown。

先写 YAML 再改，等于重写。等这三件事定了，一次写完。

---

## 到时候必须注意

- **不要把 `local-materials/` 打进构建产物。** VitePress 的 `srcDir` 只指向 `docs/`。
- **构建前跑一次敏感信息扫描**，防止 `.env`、token 混进 `docs/`。
- **`.obsidian/` 已在 `.gitignore`**，不会上传。
- Actions 权限用最小集：`contents: read`、`pages: write`、`id-token: write`。
