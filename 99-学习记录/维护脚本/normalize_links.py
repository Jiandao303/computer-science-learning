"""统一修正 vault 内 Markdown 的 WikiLink 形式。

问题：四门课各有 00-课程总览.md / 01-课程目录.md / 04-学习进度.md，裸链接
[[00-课程总览]] 在 Obsidian 中会歧义；而 [[CMU 15-122 - 课程总览]] 这种
「显示名当文件名」的写法会解析成不存在的文件，形成断链。

修正策略：
1. [[CMU 15-XXX - 课程总览]] -> [[NN-CMU-15-XXX/00-课程总览|CMU 15-XXX - 课程总览]]
2. [[CMU 15-XXX - 课程目录]] -> [[NN-CMU-15-XXX/01-课程目录|CMU 15-XXX - 课程目录]]
3. [[CMU 15-XXX - 学习进度]] -> [[NN-CMU-15-XXX/04-学习进度|CMU 15-XXX - 学习进度]]
4. [[计算机专业术语词典]] -> [[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]

只改链接写法，不改任何正文内容。已带路径的链接（含 "/"）一律跳过。
"""
import json
import os
import re
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

COURSE_DIR = {
    "15-122": "10-CMU-15-122",
    "15-213": "20-CMU-15-213",
    "15-214": "30-CMU-15-214",
    "15-445": "40-CMU-15-445",
}

SUFFIX_MAP = {
    "课程总览": "00-课程总览",
    "课程目录": "01-课程目录",
    "学习进度": "04-学习进度",
}

GLOSSARY_OLD = "[[计算机专业术语词典]]"
GLOSSARY_NEW = "[[95-计算机术语词典/Computer-Science-Glossary|计算机专业术语词典]]"

SKIP_DIRS = {"_scout", ".git", ".ruff_cache", "cache", "node_modules", "提示词.md"}


def iter_md():
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for fn in files:
            if fn.lower().endswith(".md"):
                yield os.path.join(root, fn)


def fix_links(text):
    changes = []

    def repl_course(m):
        course = m.group(1)
        suffix = m.group(2)
        target = SUFFIX_MAP.get(suffix)
        folder = COURSE_DIR.get(course)
        if not target or not folder:
            return m.group(0)
        new = "[[%s/%s|CMU %s - %s]]" % (folder, target, course, suffix)
        if new == m.group(0):
            return m.group(0)
        changes.append([m.group(0), new])
        return new

    text = re.sub(
        r"\[\[CMU (15-\d{3}) - (课程总览|课程目录|学习进度)\]\]",
        repl_course,
        text,
    )

    if GLOSSARY_OLD in text:
        n = text.count(GLOSSARY_OLD)
        text = text.replace(GLOSSARY_OLD, GLOSSARY_NEW)
        changes.append([GLOSSARY_OLD, "%s（%d 处）" % (GLOSSARY_NEW, n)])

    return text, len(changes), changes


def main():
    dry = "--dry" in sys.argv
    report = []
    for path in iter_md():
        rel = os.path.relpath(path, VAULT)
        if rel == "提示词.md":
            continue
        with open(path, "r", encoding="utf-8") as f:
            old = f.read()
        new, count, changes = fix_links(old)
        if count:
            report.append({"file": rel, "count": count, "changes": changes[:6]})
            if not dry:
                with open(path, "w", encoding="utf-8", newline="\n") as f:
                    f.write(new)

    total = sum(r["count"] for r in report)
    print("模式: %s" % ("DRY-RUN" if dry else "已写入"))
    print("受影响文件: %d, 链接修正种类数: %d" % (len(report), total))
    for r in report:
        print("  %s  (%d 类)" % (r["file"], r["count"]))
        for a, b in r["changes"]:
            print("      %s -> %s" % (a, b))

    out = os.path.join(VAULT, "99-学习记录", "link-normalize-report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print("明细已写入: 99-学习记录/link-normalize-report.json")


if __name__ == "__main__":
    main()
