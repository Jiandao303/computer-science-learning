# -*- coding: utf-8 -*-
"""CMU 课程公开资料下载器。

用法：
    python 99-学习记录/维护脚本/downloader.py jobs/15-122.json

行为：
- 只下载 jobs 文件里显式列出的公开 URL；
- 目标文件已存在时跳过，绝不覆盖（同名不同来源时自动加序号）；
- 每个文件记录 url / local_path / status / size / sha256 / fetched_at / 课程年份 / 许可；
- 403、404、连接失败只记录原因，不绕过。

清单字段：url, local_path, status, size, sha256, fetched_at(YYYY-MM-DD HH:MM:SS),
course, semester, license, title, note
"""
import hashlib
import json
import os
import sys
import time

import requests

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MANIFEST = os.path.join(ROOT, "99-学习记录", "download-manifest.json")
BINARY_EXT = (".tgz", ".tar", ".gz", ".zip", ".java", ".txt", ".pdf", ".pptx")


def load_manifest():
    if os.path.exists(MANIFEST):
        with open(MANIFEST, encoding="utf-8") as f:
            return json.load(f)
    return {"note": "本文件由 downloader.py 自动生成，记录每个下载文件的来源与校验信息。", "items": []}


def unique_path(path):
    """目标已存在则追加 -2/-3，保留旧文件。"""
    if not os.path.exists(path):
        return path
    base, ext = os.path.splitext(path)
    i = 2
    while os.path.exists("%s-%d%s" % (base, i, ext)):
        i += 1
    return "%s-%d%s" % (base, i, ext)


def fetch(job):
    url = job["url"]
    dest = os.path.join(ROOT, job["dest"])
    rec = {
        "url": url,
        "local_path": job["dest"].replace("\\", "/"),
        "course": job.get("course", ""),
        "semester": job.get("semester", ""),
        "license": job.get("license", "未标注（仅个人学习存档，见 03-资料来源与版权记录.md）"),
        "title": job.get("title", ""),
        "fetched_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    if os.path.exists(dest):
        rec.update(status=200, size=os.path.getsize(dest), note="文件已存在，跳过下载")
        with open(dest, "rb") as f:
            rec["sha256"] = hashlib.sha256(f.read()).hexdigest()
        print("SKIP %-70s %s" % (job["dest"], rec["size"]))
        return rec

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    try:
        r = requests.get(url, headers={"User-Agent": UA}, timeout=120, stream=True)
    except Exception as e:  # 网络异常：记录不中断
        rec.update(status=0, note="连接异常：%s: %s" % (type(e).__name__, e))
        print("ERR  %-70s %s" % (url, e))
        return rec

    rec["status"] = r.status_code
    if r.status_code != 200:
        rec["note"] = "HTTP %d，未保存（访问受限或文件不存在）" % r.status_code
        print("FAIL %-70s HTTP %d" % (url, r.status_code))
        return rec

    tmp = dest + ".part"
    h = hashlib.sha256()
    n = 0
    with open(tmp, "wb") as f:
        for chunk in r.iter_content(65536):
            if chunk:
                f.write(chunk)
                h.update(chunk)
                n += len(chunk)
    if n < 2048 and not dest.lower().endswith(BINARY_EXT):
        os.remove(tmp)
        rec["note"] = "响应仅 %d 字节，疑似错误页，未保存" % n
        print("TINY %-70s %d" % (url, n))
        return rec
    final = unique_path(dest)
    os.replace(tmp, final)
    rec["local_path"] = os.path.relpath(final, ROOT).replace("\\", "/")
    rec["size"] = n
    rec["sha256"] = h.hexdigest()
    print("OK   %-70s %8d" % (rec["local_path"], n))
    return rec


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    with open(sys.argv[1], encoding="utf-8") as f:
        jobs = json.load(f)
    m = load_manifest()
    for job in jobs:
        rec = fetch(job)
        m["items"] = [i for i in m["items"]
                      if not (i.get("url") == rec["url"] and i.get("local_path") == rec["local_path"])]
        m["items"].append(rec)
        with open(MANIFEST, "w", encoding="utf-8") as f:
            json.dump(m, f, ensure_ascii=False, indent=1)
    print("\n清单共 %d 条：%s" % (len(m["items"]), MANIFEST))


if __name__ == "__main__":
    main()
