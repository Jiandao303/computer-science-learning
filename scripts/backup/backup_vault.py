#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对现有 Vault 做只读备份：复制全部 Markdown 与 .obsidian 配置到 99-学习记录/备份/<日期>/。

设计原则
--------
1. 只读源目录，只写备份目录，绝不删除或移动任何原文件。
2. 备份目录自身被排除，避免递归复制成灾。
3. 记录每个文件的相对路径、字节数、sha256，生成 BACKUP-MANIFEST.json 供日后核对。
4. 已存在的备份目录默认跳过（不覆盖），除非传入 --force。

用法
----
    python scripts/backup/backup_vault.py                 # 备份到 99-学习记录/备份/<今天>/
    python scripts/backup/backup_vault.py --label before-upgrade
    python scripts/backup/backup_vault.py --dry-run
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
from datetime import datetime

VAULT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_ROOT = os.path.join(VAULT, "99-学习记录", "备份")

# 需要备份的内容：全部 Markdown + Obsidian 配置（.obsidian 整个目录）
INCLUDE_SUFFIXES = {".md"}
INCLUDE_DIRS = {".obsidian"}

# 永不备份的目录：体积大、可再生、或就是备份目录本身
EXCLUDE_DIRS = {
    "备份", "_scout", "cache", ".ruff_cache", ".git", "node_modules",
    "90-原始PDF",  # 原始 PDF 本轮不改动，且 208MB；需要时加 --with-pdfs
}


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def walk_files(with_pdfs: bool):
    """产出相对于 VAULT 的文件路径，跳过 EXCLUDE_DIRS 与备份目录本身。"""
    for root, dirs, files in os.walk(VAULT):
        rel_root = os.path.relpath(root, VAULT)
        rel_parts = () if rel_root == "." else tuple(rel_root.split(os.sep))
        inside_obsidian = bool(rel_parts) and rel_parts[0] in INCLUDE_DIRS

        # 目录剪枝：只按排除名单剪；.obsidian 不在名单里，因此会被保留
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

        for name in files:
            rel = name if rel_root == "." else os.path.join(rel_root, name)
            parts = tuple(rel.split(os.sep))
            if not inside_obsidian and any(p in EXCLUDE_DIRS for p in parts[:-1]):
                continue
            suffix = os.path.splitext(name)[1].lower()
            if inside_obsidian or suffix in INCLUDE_SUFFIXES or (
                with_pdfs and suffix == ".pdf"
            ):
                yield rel


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default="", help="备份目录后缀，如 before-upgrade")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true", help="目标已存在时覆盖")
    ap.add_argument("--with-pdfs", action="store_true", help="连 90-原始PDF 一起备份（约 208MB）")
    args = ap.parse_args()

    stamp = datetime.now().strftime("%Y-%m-%d")
    folder = f"{stamp}-{args.label}" if args.label else stamp
    dest = os.path.join(BACKUP_ROOT, folder)

    files = sorted(walk_files(args.with_pdfs))
    records = []
    total = 0
    for rel in files:
        src = os.path.join(VAULT, rel)
        size = os.path.getsize(src)
        total += size
        records.append({"path": rel.replace(os.sep, "/"), "bytes": size, "sha256": sha256_of(src)})

    print(f"Vault      : {VAULT}")
    print(f"备份目标   : {dest}")
    print(f"待备份文件 : {len(files)} 个，共 {total / 1024 / 1024:.2f} MB")
    if args.dry_run:
        for r in records[:10]:
            print(f"  [dry] {r['path']}  {r['bytes']}B")
        if len(records) > 10:
            print(f"  ... 其余 {len(records) - 10} 个省略")
        return 0

    if os.path.exists(dest) and not args.force:
        print(f"目标已存在，跳过：{dest}（如需覆盖加 --force）", file=sys.stderr)
        return 1

    for r in records:
        src = os.path.join(VAULT, r["path"].replace("/", os.sep))
        dst = os.path.join(dest, r["path"].replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)

    manifest = {
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vault_root": VAULT,
        "backup_dir": dest,
        "file_count": len(records),
        "total_bytes": total,
        "note": "只备份 Markdown 与 .obsidian 配置；原始 PDF 未改动故未备份（--with-pdfs 可一并备份）",
        "files": records,
    }
    mpath = os.path.join(dest, "BACKUP-MANIFEST.json")
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"完成：{len(records)} 个文件 -> {dest}")
    print(f"清单：{mpath}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
