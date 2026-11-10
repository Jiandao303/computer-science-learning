#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""批量核验候选课程网址的 HTTP 状态，输出可复现的核验结果。

背景：知识库的课程资源索引必须只收录真实可达的网址。本脚本把候选清单
逐条请求一次（GET，只读前 8KB），把 200/3xx 记为可达、4xx/5xx/超时记为不可达。

用法：
    python scripts/verify_urls.py                 # 核验并写 sources/_url-check.json
    python scripts/verify_urls.py --dry-run       # 只打印清单
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request

VAULT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(VAULT, "sources", "_url-check.json")

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

# 候选清单：domain -> [(课程/资源名, URL)]
CANDIDATES: dict[str, list[tuple[str, str]]] = {
    "数学基础": [
        ("MIT 18.06 Linear Algebra", "https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/"),
        ("MIT 6.042J Mathematics for Computer Science", "https://ocw.mit.edu/courses/6-042j-mathematics-for-computer-science-fall-2010/"),
        ("MIT 6.041 Probabilistic Systems Analysis", "https://ocw.mit.edu/courses/6-041-probabilistic-systems-analysis-and-applied-probability-fall-2010/"),
        ("Berkeley CS 70", "https://www.eecs70.org/"),
        ("Stanford CS 109", "https://web.stanford.edu/class/cs109/"),
        ("MIT 18.404J Theory of Computation", "https://ocw.mit.edu/courses/18-404j-theory-of-computation-fall-2020/"),
    ],
    "编程基础": [
        ("Harvard CS50x", "https://cs50.harvard.edu/x/"),
        ("Berkeley CS 61A", "https://cs61a.org/"),
        ("MIT 6.100L", "https://ocw.mit.edu/courses/6-100l-introduction-to-cs-and-programming-using-python-fall-2022/"),
        ("CMU 15-112", "https://www.cs.cmu.edu/~112/"),
        ("SICP 在线全文", "https://mitp-content-server.mit.edu/books/content/sectbyfn/books_pres_0/6515/sicp.zip/index.html"),
        ("Python 官方教程", "https://docs.python.org/3/tutorial/"),
    ],
    "数据结构与算法": [
        ("MIT 6.006 Introduction to Algorithms", "https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-spring-2020/"),
        ("Princeton Algorithms (Sedgewick)", "https://algs4.cs.princeton.edu/"),
        ("Berkeley CS 61B", "https://cs61b.org/"),
        ("Stanford CS 161", "https://web.stanford.edu/class/cs161/"),
        ("CP-Algorithms", "https://cp-algorithms.com/"),
        ("CMU 15-122 Fall 2026", "https://www.cs.cmu.edu/~15122-archive/f26/"),
    ],
    "计算机组成": [
        ("CMU 15-213 Fall 2026", "https://www.cs.cmu.edu/~213/"),
        ("Berkeley CS 61C", "https://cs61c.org/"),
        ("Nand2Tetris", "https://www.nand2tetris.org/"),
        ("MIT 6.004 Computation Structures", "https://ocw.mit.edu/courses/6-004-computation-structures-spring-2017/"),
        ("CSAPP 教材站", "https://csapp.cs.cmu.edu/"),
    ],
    "操作系统": [
        ("MIT 6.S081 / 6.828", "https://pdos.csail.mit.edu/6.S081/2021/schedule.html"),
        ("OSTEP 教材", "https://pages.cs.wisc.edu/~remzi/OSTEP/"),
        ("Berkeley CS 162", "https://cs162.org/"),
        ("CMU 15-410", "https://www.cs.cmu.edu/~410/"),
    ],
    "计算机网络": [
        ("Stanford CS 144", "https://cs144.github.io/"),
        ("Kurose & Ross 教材站", "https://gaia.cs.umass.edu/kurose_ross/index.php"),
        ("CMU 15-441", "https://computer-networks.github.io/fa20/"),
    ],
    "数据库": [
        ("CMU 15-445 Fall 2026", "https://15445.courses.cs.cmu.edu/fall2026/"),
        ("Berkeley CS 186", "https://cs186berkeley.net/"),
        ("Database System Concepts 教材站", "https://db-book.com/"),
        ("PostgreSQL 文档", "https://www.postgresql.org/docs/"),
        ("SQLite 文档", "https://www.sqlite.org/docs.html"),
    ],
    "编译原理": [
        ("Stanford CS 143", "https://web.stanford.edu/class/cs143/"),
        ("Crafting Interpreters", "https://craftinginterpreters.com/"),
        ("LLVM Kaleidoscope 教程", "https://llvm.org/docs/tutorial/"),
        ("CMU 15-411", "https://www.cs.cmu.edu/~fp/courses/15411-f08/"),
    ],
    "软件工程": [
        ("CMU 15-214 Fall 2013", "https://www.cs.cmu.edu/~aldrich/214/"),
        ("MIT 6.031 Software Construction", "https://web.mit.edu/6.031/www/sp21/"),
        ("Google Engineering Practices", "https://google.github.io/eng-practices/"),
        ("Martin Fowler", "https://martinfowler.com/"),
        ("Refactoring Guru 设计模式", "https://refactoring.guru/design-patterns"),
    ],
    "前端开发": [
        ("MDN Web Docs", "https://developer.mozilla.org/zh-CN/"),
        ("web.dev", "https://web.dev/"),
        ("javascript.info", "https://javascript.info/"),
        ("React 官方文档", "https://react.dev/"),
        ("Vue 官方文档", "https://cn.vuejs.org/"),
        ("TypeScript 手册", "https://www.typescriptlang.org/docs/handbook/intro.html"),
    ],
    "后端开发": [
        ("MIT 6.033 Computer System Engineering", "https://ocw.mit.edu/courses/6-033-computer-system-engineering-spring-2018/"),
        ("The Twelve-Factor App", "https://12factor.net/zh_cn/"),
        ("Node.js 文档", "https://nodejs.org/docs/latest/api/"),
        ("Spring Guides", "https://spring.io/guides"),
        ("FastAPI 文档", "https://fastapi.tiangolo.com/"),
    ],
    "软件安全": [
        ("OWASP Top 10", "https://owasp.org/www-project-top-ten/"),
        ("SEED Labs", "https://seedsecuritylabs.org/"),
        ("PortSwigger Web Security Academy", "https://portswigger.net/web-security"),
        ("MIT 6.858 Computer Systems Security", "https://css.csail.mit.edu/6.858/"),
        ("CWE", "https://cwe.mitre.org/"),
    ],
    "DevOps与运维": [
        ("Google SRE Book", "https://sre.google/sre-book/table-of-contents/"),
        ("Docker 文档", "https://docs.docker.com/"),
        ("Kubernetes 文档", "https://kubernetes.io/docs/home/"),
        ("GitHub Actions 文档", "https://docs.github.com/en/actions"),
        ("Linux 命令行入门 (TLCL)", "https://linuxcommand.org/tlcl.php"),
    ],
    "分布式系统": [
        ("MIT 6.824", "https://pdos.csail.mit.edu/6.824/"),
        ("Raft 共识算法", "https://raft.github.io/"),
        ("Jepsen", "https://jepsen.io/"),
        ("CMU 15-440", "https://www.cs.cmu.edu/~440/"),
    ],
    "系统架构": [
        ("System Design Primer", "https://github.com/donnemartin/system-design-primer"),
        ("AWS Well-Architected", "https://aws.amazon.com/architecture/well-architected/"),
        ("Azure Architecture Center", "https://learn.microsoft.com/en-us/azure/architecture/"),
        ("12-Factor App", "https://12factor.net/"),
    ],
    "计算机高级选修": [
        ("Stanford CS 229 Machine Learning", "https://cs229.stanford.edu/"),
        ("Stanford CS 231N", "https://cs231n.stanford.edu/"),
        ("Stanford CS 224N", "https://web.stanford.edu/class/cs224n/"),
        ("CMU 15-462 Computer Graphics", "https://15462.courses.cs.cmu.edu/"),
        ("CMU 15-418 Parallel Computer Architecture", "https://www.cs.cmu.edu/~418/"),
        ("CMU 15-312 Foundations of Programming Languages", "https://www.cs.cmu.edu/~crary/312/"),
        ("Berkeley CS 285 Deep RL", "https://rail.eecs.berkeley.edu/deeprlcourse/"),
    ],
}


def _check_urllib(url: str, timeout: int) -> tuple[int | str, str]:
    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Connection": "close",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as e:
        return e.code, ""
    except Exception as e:  # noqa: BLE001
        return "ERR", type(e).__name__


def _check_curl(url: str, timeout: int) -> tuple[int | str, str]:
    """部分站点会按客户端指纹拒绝 urllib（如 CMU 返回 503），用 curl 复核。

    这里只做一次只读 GET，不跟随无限重定向。curl 不可用时返回 ERR。
    """
    if not shutil.which("curl"):
        return "ERR", "no-curl"
    try:
        out = subprocess.run(
            ["curl", "-L", "-s", "-o", os.devnull, "-m", str(timeout),
             "-w", "%{http_code} %{url_effective}",
             "-A", UA + " (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
             url],
            capture_output=True, text=True, timeout=timeout + 10,
        )
        code, _, final = out.stdout.partition(" ")
        return (int(code) if code.isdigit() and code != "000" else "ERR"), final.strip()
    except Exception as e:  # noqa: BLE001
        return "ERR", type(e).__name__


def check(url: str, timeout: int = 20) -> tuple[int | str, str, str]:
    status, final = _check_urllib(url, timeout)
    ok = isinstance(status, int) and status < 400
    if ok:
        return status, final, "urllib"
    # 4xx 是明确的服务器答复，不再复核；只有 503/429/网络错误才可能是客户端指纹问题
    if status in (503, 429, "ERR"):
        s2, f2 = _check_curl(url, timeout)
        if isinstance(s2, int) and s2 < 400:
            return s2, f2, "curl"
        return status, final, "urllib+curl"
    return status, final, "urllib"


def write_markdown(results: list[dict], ok: int, bad: int) -> None:
    """把核验结果渲染成人读的 Markdown 总表。"""
    out = os.path.join(VAULT, "sources", "01-课程资源总表.md")
    lines = [
        "# 课程资源总表",
        "",
        "> 本文件由 `python scripts/verify_urls.py` 自动生成，**请勿手改**。",
        f"> 共 {len(results)} 条，可达 {ok} 条，不可达 {bad} 条。",
        "> 「网络不可达」是本机到该站点连不上（DNS/连接失败），不代表网址失效。",
        "",
    ]
    cur = None
    for r in results:
        if r["domain"] != cur:
            cur = r["domain"]
            lines += ["", f"## {cur}", "",
                      "| 资源 | 状态 | 链接 |", "| --- | --- | --- |"]
        if r["reachable"]:
            state = "✅ 可达"
        elif r["status"] == "ERR":
            state = "⚠ 网络不可达"
        else:
            state = f"⚠ HTTP {r['status']}"
        lines.append(f"| {r['name']} | {state} | <{r['url']}> |")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lines) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    total = sum(len(v) for v in CANDIDATES.values())
    print(f"候选网址 {total} 条，覆盖 {len(CANDIDATES)} 个领域")
    if args.dry_run:
        for domain, items in CANDIDATES.items():
            print(f"[{domain}] {len(items)} 条")
        return 0

    results = []
    ok = bad = 0
    for domain, items in CANDIDATES.items():
        for name, url in items:
            status, final, via = check(url)
            reachable = isinstance(status, int) and status < 400
            if reachable:
                ok += 1
            else:
                bad += 1
            results.append({
                "domain": domain, "name": name, "url": url,
                "status": status, "reachable": reachable,
                "final_url": final, "via": via,
            })
            print(f"{'OK ' if reachable else 'BAD'} {status:<4} [{domain}] {name}")

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({
            "checked_with": "scripts/verify_urls.py",
            "total": total, "reachable": ok, "unreachable": bad,
            "results": results,
        }, f, ensure_ascii=False, indent=2)
    write_markdown(results, ok, bad)
    print(f"\n可达 {ok} / 不可达 {bad}，结果写入 {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
