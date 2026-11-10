# scripts —— 自动化脚本区

> ✅ **这个目录会公开。** 脚本本身不含版权内容，是这份知识库的"基础设施"。

---

## 现有脚本

| 脚本 | 作用 | 用法 |
| --- | --- | --- |
| `backup/backup_vault.py` | 备份全部 `.md` 与 `.obsidian/` 到 `99-学习记录/备份/<日期>/`，附 sha256 清单 | `python scripts/backup/backup_vault.py --label <名字>` |
| `verify_urls.py` | 核验 16 领域 80 条课程网址可达性，输出 `sources/_url-check.json` | `python scripts/verify_urls.py` |
| `scaffold_domains.py` | 为 16 个领域生成 `docs/<领域>/{00,01,02}.md`，已存在则跳过 | `python scripts/scaffold_domains.py` |

升级前已有的脚本仍在 `99-学习记录/维护脚本/`：`downloader.py`、`make_jobs.py`、`gen_sources.py`、`normalize_links.py`、`fix_note_links.py`、`check_links.py`、`quality_check.py`。按"不移动现有文件"的要求，**未搬迁**。

---

## 写作约定

- **幂等**：重复运行不产生重复内容。已存在的文件默认跳过，不覆盖。
- **只读优先**：涉及删除/覆盖的脚本必须有 `--dry-run`。
- **路径从脚本位置推导**，不要硬编码 `D:\work file\...`：

```python
ROOT = Path(__file__).resolve().parent.parent
```

- **中文输出**：Windows 下先设 `PYTHONIOENCODING=utf-8`，否则 `print` 中文会 `UnicodeEncodeError`。
- **不写网络重试循环**：失败就记录失败，不无限重试。

---

## 计划中的脚本

| 脚本 | 作用 | 优先级 |
| --- | --- | --- |
| `check_frontmatter.py` | 校验 `docs/` 每页是否有标题、日期、来源字段 | 高 |
| `build_index.py` | 扫描 `docs/` 生成总目录，避免手写索引过期 | 高 |
| `sync_notes.py` | 把 `personal-notes/` 里标记为"可公开"的笔记搬到 `docs/` | 中 |
| `check_links.py`（升级版） | 支持 16 领域 WikiLink 与外部 URL 混合校验 | 中 |
