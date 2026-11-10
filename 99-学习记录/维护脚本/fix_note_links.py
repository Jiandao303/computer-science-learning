# -*- coding: utf-8 -*-
"""修复笔记间 WikiLink 断链。

处理四类断链：
1. 别名式课程级链接：[[CMU 15-122 - 课程总览]] -> [[10-CMU-15-122/00-课程总览|CMU 15-122 - 课程总览]]
2. 别名式讲次链接：[[CMU 15-213 - L02 Bits, Bytes, and Integers]] -> [[15-213-02-Bits-Bytes-and-Integers|...]]
3. 讲次号写错：[[15-122-13-Queues]] -> 实际文件 [[15-122-09-Stacks-and-Queues]]
4. 词典链接：[[计算机专业术语词典]] -> [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]

只改链接文本，不动正文；已能解析的链接一律不碰。
"""
import os
import re
import json
import glob
import difflib

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(VAULT)

LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(\|[^\]]*)?\]\]")

COURSE_DIR = {
    "15-122": "10-CMU-15-122",
    "15-213": "20-CMU-15-213",
    "15-214": "30-CMU-15-214",
    "15-445": "40-CMU-15-445",
}

COURSE_PAGE = {
    "课程总览": "00-课程总览",
    "课程目录": "01-课程目录",
    "学习进度": "04-学习进度",
    "练习与复盘总览": "03-练习与复盘/00-练习与复盘总览",
    "Lab总览": "03-Lab实验笔记/00-Lab总览",
    "项目总览": "03-项目学习笔记/00-项目总览",
}

GLOSSARY_TARGET = "95-计算机术语词典/Computer-Science-Glossary"


def load_notes():
    """返回 (by_num, by_slug, all_names)。"""
    by_num, by_slug, all_names = {}, {}, set()
    for course, d in COURSE_DIR.items():
        by_num[course], by_slug[course] = {}, {}
        p = os.path.join(d, "02-中文学习笔记")
        if not os.path.isdir(p):
            continue
        for f in sorted(os.listdir(p)):
            if not f.endswith(".md"):
                continue
            base = f[:-3]
            parts = base.split("-", 3)  # 15-122-01-Contracts
            if len(parts) < 4:
                continue
            by_num[course].setdefault(parts[2], base)
            by_slug[course][parts[3].lower()] = base
    for p in glob.glob("**/*.md", recursive=True):
        if p.startswith("_scout"):
            continue
        all_names.add(os.path.basename(p)[:-3])
    return by_num, by_slug, all_names


def resolve(target, by_num, by_slug, all_names):
    if target.startswith("http"):
        return target
    if "/" in target:
        if os.path.isfile(target + ".md") or os.path.isfile(target):
            return target
        return None
    if target in all_names:
        return target
    return None


def repair(target, alias, by_num, by_slug, all_names):
    """尝试把断链目标改写成能解析的形式；返回 (new_target, new_alias) 或 None。"""
    raw = target

    # 4. 词典
    if raw in ("计算机专业术语词典", "术语词典", "Computer-Science-Glossary"):
        return GLOSSARY_TARGET, alias or "计算机专业术语词典"

    # 1. 别名式课程级链接
    m = re.match(r"^CMU (15-\d{3}) - (.+)$", raw)
    if m:
        course, rest = m.group(1), m.group(2).strip()
        # 1b. 别名式讲次链接 CMU 15-213 - L02 Bits, Bytes, and Integers
        lm = re.match(r"^L(\d{2})\s+(.+)$", rest)
        if lm:
            num, title = lm.group(1), lm.group(2)
            base = by_num.get(course, {}).get(num)
            if base is None:
                key = title.lower().replace(",", "").replace(" ", "-")
                cand = difflib.get_close_matches(
                    key, list(by_slug.get(course, {}).keys()), n=1, cutoff=0.4)
                if cand:
                    base = by_slug[course][cand[0]]
            if base:
                return base, alias or raw
            return None
        # 1c. 课程级页面
        for key, rel in COURSE_PAGE.items():
            if key in rest:
                d = COURSE_DIR.get(course)
                if d:
                    return "%s/%s" % (d, rel), alias or raw
        return None

    # 3. 讲次号写错：15-122-13-Queues
    # 只在「slug 能在已有笔记里唯一匹配到」时才改，避免把「笔记尚未写完」误判成错号。
    m = re.match(r"^(15-\d{3})-(\d{2})-(.+)$", raw)
    if m:
        course, num, slug = m.group(1), m.group(2), m.group(3)
        slugs = by_slug.get(course, {})
        key = slug.lower()
        # 3a. slug 完全一致 -> 用真实讲次号
        if key in slugs:
            base = slugs[key]
            return (base, alias) if base != raw else None
        # 3b. slug 是某个已有 slug 的子串（或反之），且唯一 -> 用那个
        hits = [b for s, b in slugs.items() if key in s or s in key]
        if len(hits) == 1:
            return hits[0], alias
        # 3c. 该讲次号存在但 slug 不同 -> 不动（可能是笔记未写，留给后续补齐）
        return None

    return None


SKIP = ("_scout", "提示词.md", "99-学习记录")


def main():
    by_num, by_slug, all_names = load_notes()
    report = []
    for p in glob.glob("**/*.md", recursive=True):
        if p.startswith(SKIP):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        changes = []

        def sub(m):
            target = m.group(1).strip()
            alias = (m.group(2) or "")[1:] if m.group(2) else ""
            clean = target.replace(chr(92), "").strip()
            if resolve(clean, by_num, by_slug, all_names):
                return m.group(0)
            fixed = repair(clean, alias, by_num, by_slug, all_names)
            if not fixed:
                return m.group(0)
            new_target, new_alias = fixed
            if new_alias:
                new = "[[%s|%s]]" % (new_target, new_alias)
            else:
                new = "[[%s]]" % new_target
            changes.append([m.group(0), new])
            return new

        new_text = LINK_RE.sub(sub, text)
        if changes:
            report.append({"file": p, "count": len(changes), "changes": changes})
            if "--dry" not in os.sys.argv:
                with open(p, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new_text)

    total = sum(r["count"] for r in report)
    print("受影响文件: %d" % len(report))
    print("修正链接数: %d" % total)
    for r in report[:15]:
        print("  %s (%d)" % (r["file"], r["count"]))
        for old, new in r["changes"][:2]:
            print("      %s -> %s" % (old, new))
    with open("99-学习记录/fix-links-report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=1)
    print("明细: 99-学习记录/fix-links-report.json")


if __name__ == "__main__":
    main()
