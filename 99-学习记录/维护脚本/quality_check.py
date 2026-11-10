"""Vault 质量检查脚本。

检查项（对应提示词.md 528-567 行的质量要求）：
 1. 文件存在与大小（空文件、过小文件）
 2. 重复文件（同 sha256）
 3. 文件名规范（Markdown 是否遵循编号-名称 形式）
 4. 扩展名正确性
 5. YAML frontmatter 完整性与必需字段
 6. 12 节标题层级完整性
 7. 内部 WikiLink 断链检测
 8. 来源可追溯（每篇笔记第 8 节须含 PDF 路径或原始链接）
 9. C0 / C 混淆检测（15-122 前 16 讲不得只提 C 不提 C0）
10. 学期混用检测（15-214 不得出现 2026；15-445 引用 2025 视频须标注年份）

输出：99-学习记录/quality-report.json 与终端摘要。
"""
import hashlib
import json
import os
import re
from collections import defaultdict

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SKIP_DIRS = {"_scout", ".git", ".ruff_cache", "cache", "node_modules"}

REQUIRED_YAML = [
    "course", "course_name", "semester", "lecture_id",
    "topic", "language", "source_language", "status", "tags",
]

REQUIRED_SECTIONS = [
    "## 1. 本节学习目标", "## 2. 前置知识", "## 3. 核心概念", "## 4. 通俗理解",
    "## 5. 原理与推导", "## 6. 代码示例", "## 7. 容易混淆的概念", "## 8. 对应原版讲义",
    "## 9. 对应视频", "## 10. 本节复习", "## 11. 自我检查", "## 12. 进一步学习",
]


def walk_files(exts=None):
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if exts and not fn.lower().endswith(exts):
                continue
            yield os.path.join(root, fn)


def rel(p):
    return os.path.relpath(p, VAULT).replace("\\", "/")


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_frontmatter(text):
    if not text.startswith("---"):
        return {}, False, text
    end = text.find("\n---", 3)
    if end == -1:
        return {}, False, text
    block, body = text[3:end], text[end + 4:]
    data, cur_list = {}, None
    for line in block.splitlines():
        if not line.strip():
            continue
        if line.startswith("  - ") or line.startswith("- "):
            if cur_list is not None:
                cur_list.append(line.strip()[1:].strip())
            continue
        m = re.match(r"^([A-Za-z_][\w-]*):\s*(.*)$", line)
        if m:
            key, val = m.group(1), m.group(2).strip()
            if val == "":
                cur_list = []
                data[key] = cur_list
            else:
                data[key] = val.strip('"').strip("'")
                cur_list = None
    return data, True, body


def build_link_index(md_files):
    names, paths = set(), set()
    for p in md_files:
        r = rel(p)
        paths.add(r[:-3] if r.lower().endswith(".md") else r)
        names.add(os.path.basename(r)[:-3])
    return names, paths


WIKILINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")


def main():
    report = {"checks": [], "summary": {"pass": 0, "warn": 0, "fail": 0}}

    def add(name, status, detail, items=None):
        report["checks"].append({
            "name": name, "status": status, "detail": detail,
            "items": (items or [])[:60],
        })
        report["summary"][status] = report["summary"].get(status, 0) + 1

    md_files = sorted(walk_files((".md",)))
    all_files = sorted(walk_files())

    # 1. 空文件 / 过小文件
    empties, tinies = [], []
    for p in all_files:
        if os.path.basename(p) == ".gitkeep":
            continue
        sz = os.path.getsize(p)
        if sz == 0:
            empties.append({"file": rel(p)})
        elif p.lower().endswith(".md") and sz < 200:
            tinies.append({"file": rel(p), "size": sz})
    add("空文件", "fail" if empties else "pass", "发现 %d 个 0 字节文件" % len(empties), empties)
    add("过小的 Markdown", "warn" if tinies else "pass",
        "发现 %d 个小于 200 字节的 Markdown" % len(tinies), tinies)

    # 2. 重复文件
    by_hash = defaultdict(list)
    for p in all_files:
        if os.path.getsize(p) < 512:
            continue
        try:
            by_hash[sha256_of(p)].append(rel(p))
        except OSError:
            pass
    dups = [{"sha256": k[:16], "files": v} for k, v in by_hash.items() if len(v) > 1]
    add("重复文件", "warn" if dups else "pass",
        "发现 %d 组内容完全相同的文件" % len(dups), dups)

    # 3. 笔记文件名规范
    bad_names = []
    for p in md_files:
        r = rel(p)
        if any(x in r for x in ("/02-中文学习笔记/", "/03-Lab实验笔记/", "/03-项目学习笔记/", "/03-练习与复盘/")):
            if not re.match(r"^15-\d{3}-\d{2}-[A-Za-z0-9-]+\.md$", os.path.basename(r)):
                bad_names.append({"file": r})
    add("笔记文件名规范", "warn" if bad_names else "pass",
        "%d 个笔记文件名不符合 `15-XXX-NN-Name.md` 规范" % len(bad_names), bad_names)

    # 4. 扩展名
    allowed = {".md", ".pdf", ".tgz", ".tar", ".txt", ".json", ".py", ".zip",
               ".java", ".png", ".jpg", ".gif", ".svg", ".html", ".ics", ".csv"}
    bad_ext = []
    for p in all_files:
        e = os.path.splitext(p)[1].lower()
        if e and e not in allowed:
            bad_ext.append({"file": rel(p), "ext": e})
    add("扩展名", "warn" if bad_ext else "pass",
        "%d 个文件的扩展名不在白名单内" % len(bad_ext), bad_ext)

    # 5. YAML
    yaml_missing, yaml_incomplete, note_files = [], [], []
    for p in md_files:
        r = rel(p)
        if not any(x in r for x in ("/02-中文学习笔记/", "/03-Lab实验笔记/", "/03-项目学习笔记/")):
            continue
        note_files.append(p)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        data, ok, _ = parse_frontmatter(text)
        if not ok:
            yaml_missing.append({"file": r})
            continue
        miss = [k for k in REQUIRED_YAML if k not in data]
        if miss:
            yaml_incomplete.append({"file": r, "missing": miss})
    add("YAML 缺失", "fail" if yaml_missing else "pass",
        "%d 篇笔记完全没有 YAML frontmatter" % len(yaml_missing), yaml_missing)
    add("YAML 字段完整性", "warn" if yaml_incomplete else "pass",
        "%d 篇笔记 YAML 缺少必需字段" % len(yaml_incomplete), yaml_incomplete)

    # 6. 12 节结构
    section_issues = []
    for p in note_files:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        miss = [s for s in REQUIRED_SECTIONS if s not in text]
        if miss:
            section_issues.append({"file": rel(p), "missing_sections": miss})
    add("12 节结构完整性", "warn" if section_issues else "pass",
        "%d 篇笔记缺少必需章节" % len(section_issues), section_issues)

    # 7. 断链
    names, paths = build_link_index(md_files)
    broken = []
    for p in md_files:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        for m in WIKILINK_RE.finditer(text):
            target = m.group(1).strip().rstrip("\\")  # 表格内转义竖线会残留反斜杠
            if not target or target.startswith("http"):
                continue
            base = target[:-3] if target.lower().endswith(".md") else target
            ok = (base in paths) if "/" in base else (base in names)
            if not ok:
                broken.append({"file": rel(p), "target": target})
    add("内部链接断链", "warn" if broken else "pass",
        "发现 %d 处可能断链的 WikiLink" % len(broken), broken)

    # 8. 来源可追溯
    no_source = []
    for p in note_files:
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        idx = text.find("## 8. 对应原版讲义")
        if idx == -1:
            continue
        seg = text[idx: idx + 2000]
        if "90-原始PDF" not in seg and "http" not in seg:
            no_source.append({"file": rel(p)})
    add("来源可追溯（第 8 节）", "warn" if no_source else "pass",
        "%d 篇笔记第 8 节未出现 PDF 路径或原始链接" % len(no_source), no_source)

    # 9. C0 / C 混淆
    c0_issues = []
    for p in note_files:
        r = rel(p)
        if not r.startswith("10-CMU-15-122/"):
            continue
        m = re.search(r"15-122-(\d{2})-", os.path.basename(r))
        if not m:
            continue
        lec = int(m.group(1))
        if lec > 16:
            continue
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if "C0" not in text:
            c0_issues.append({"file": r, "lecture": lec, "reason": "前 16 讲未出现 C0 字样"})
    add("C0 / C 区分", "warn" if c0_issues else "pass",
        "%d 篇 15-122 前段笔记未提及 C0" % len(c0_issues), c0_issues)

    # 10. 学期混用
    sem_issues = []
    for p in note_files:
        r = rel(p)
        with open(p, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        if r.startswith("30-CMU-15-214/") and "2013" not in text:
            sem_issues.append({"file": r, "reason": "15-214 笔记未标注 Fall 2013"})
        if r.startswith("40-CMU-15-445/"):
            if ("youtube" in text.lower() or "youtu.be" in text.lower()) and "2025" not in text:
                sem_issues.append({"file": r, "reason": "引用 YouTube 视频但未标注 2025 年份"})
    add("学期混用", "warn" if sem_issues else "pass",
        "%d 篇笔记存在学期标注问题" % len(sem_issues), sem_issues)

    report["stats"] = {
        "markdown_count": len(md_files),
        "note_count": len(note_files),
        "pdf_count": sum(1 for p in all_files if p.lower().endswith(".pdf")),
        "total_files": len(all_files),
    }

    out = os.path.join(VAULT, "99-学习记录", "quality-report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("=" * 62)
    print("质量检查结果")
    print("=" * 62)
    for c in report["checks"]:
        mark = {"pass": "[PASS]", "warn": "[WARN]", "fail": "[FAIL]"}[c["status"]]
        print("%s %-22s %s" % (mark, c["name"], c["detail"]))
    s = report["summary"]
    print("-" * 62)
    print("通过 %d / 警告 %d / 失败 %d" % (s.get("pass", 0), s.get("warn", 0), s.get("fail", 0)))
    print("统计: Markdown %d, 笔记 %d, PDF %d, 文件总计 %d" % (
        report["stats"]["markdown_count"], report["stats"]["note_count"],
        report["stats"]["pdf_count"], report["stats"]["total_files"]))
    print("明细: 99-学习记录/quality-report.json")


if __name__ == "__main__":
    main()
