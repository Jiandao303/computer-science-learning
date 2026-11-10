#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统计 Vault 的文件/目录/体积分布，用于检查报告与进度核对。

只读，不修改任何文件。
用法：python scripts/vault_stats.py
"""
from __future__ import annotations

import collections
import os
import sys

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    ext = collections.Counter()
    top = collections.Counter()
    top_bytes = collections.Counter()
    n = d = 0
    total = 0
    for root, dirs, files in os.walk(VAULT):
        dirs[:] = [x for x in dirs if x not in (".git",)]
        d += len(dirs)
        for f in files:
            n += 1
            p = os.path.join(root, f)
            try:
                b = os.path.getsize(p)
            except OSError:
                b = 0
            total += b
            ext[os.path.splitext(f)[1].lower() or "(no-ext)"] += 1
            rel = os.path.relpath(root, VAULT)
            seg = rel.split(os.sep)[0] if rel != "." else "(root)"
            top[seg] += 1
            top_bytes[seg] += b

    print(f"文件 {n} / 目录 {d} / 合计 {total / 1048576:.1f} MB")
    print("\n扩展名分布：")
    for k, v in ext.most_common(12):
        print(f"  {k:<10} {v}")
    print("\n顶层目录（文件数 / 体积）：")
    for k, v in top.most_common(30):
        print(f"  {k:<28} {v:>5}  {top_bytes[k] / 1048576:>8.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
