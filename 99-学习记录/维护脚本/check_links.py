# -*- coding: utf-8 -*-
"""扫描 vault 内所有 Markdown 的 WikiLink，报告断链。"""
import os
import re
import glob

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(VAULT)

LINK_RE = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")

all_md = glob.glob("**/*.md", recursive=True)
names = {os.path.basename(p)[:-3] for p in all_md}

broken = {}
total = 0
for p in all_md:
    if p.startswith("_scout"):
        continue
    text = open(p, encoding="utf-8", errors="replace").read()
    for m in LINK_RE.finditer(text):
        total += 1
        target = m.group(1).strip()
        # 表格里转义的竖线会在目标末尾留下反斜杠
        target = target.replace(chr(92), "").strip()
        if not target or target.startswith("http"):
            continue
        if "/" in target:
            ok = os.path.isfile(target + ".md") or os.path.isfile(target)
        else:
            ok = target in names
        if not ok:
            broken.setdefault(target, []).append(p)

print("总 WikiLink 数:", total)
print("断链目标数:", len(broken))
for t in sorted(broken):
    print("  %-60s <- %s" % (t, ", ".join(sorted(set(broken[t]))[:3])))
