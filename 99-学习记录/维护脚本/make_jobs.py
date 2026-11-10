# -*- coding: utf-8 -*-
"""生成各课程下载任务清单（只列出课程官网公开文件）。

输出 _scout/jobs/{15-122,15-213,15-214,15-445}.json，
每个元素字段：url, dest, course, semester, license, title
供 downloader.py 读取执行。
"""
import json
import os
from urllib.parse import quote

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jobs")
os.makedirs(OUT, exist_ok=True)

LIC = "课程官网公开讲义，未标注开放许可；仅作个人学习存档，版权归 CMU 及授课教师"
LIC214 = "课程官网公开讲义（Fall 2013 历史学期），未标注开放许可；仅作个人学习存档"
LIC445 = "课程官网公开幻灯片/讲义（Fall 2026），未标注开放许可；仅作个人学习存档"


def job(url, dest, course, semester, license_text, title):
    return {"url": url, "dest": dest, "course": course, "semester": semester,
            "license": license_text, "title": title}


def dump(name, jobs):
    with open(os.path.join(OUT, name), "w", encoding="utf-8") as f:
        json.dump(jobs, f, ensure_ascii=False, indent=1)
    print(name, len(jobs))


# ---------------- 15-122 ----------------
B = "https://www.cs.cmu.edu/~15122-archive/f26/"
jobs = []
lec = ["01-contracts", "02-ints", "03-arrays", "04-linsearch", "05-bigo", "06-binsearch",
       "07-quicksort", "08-libraries", "09-stackqueue", "10-linkedlist", "11-uba", "12-hashing",
       "13-hdict", "14-generic", "15-bst", "16-avl", "17-cintro", "18-cmem", "19-cnum",
       "20-c0vm", "21-graphs", "22-dfs", "23-spanning", "24-unionfind", "25-pq", "26-heap"]
for i in lec:
    jobs.append(job(B + "handouts/lectures/%s.pdf" % i,
                    "90-原始PDF/15-122/lectures/%s.pdf" % i, "15-122", "Fall 2026", LIC,
                    "讲义 %s" % i))
    jobs.append(job(B + "handouts/code/%s.tgz" % i,
                    "90-原始PDF/15-122/code/%s.tgz" % i, "15-122", "Fall 2026", LIC,
                    "课堂示例代码 %s" % i))
for i in ["08-pointers", "12-voidstar", "14-fpointer"]:
    jobs.append(job(B + "handouts/slides/review/%s.pdf" % i,
                    "90-原始PDF/15-122/review-slides/%s.pdf" % i, "15-122", "Fall 2026", LIC,
                    "复习幻灯片 %s" % i))
for f, t in [("setup", "Setup Lab"), ("acad", "学术诚信"), ("unit_testing_notes", "单元测试笔记"),
             ("linux_quickref", "Linux 速查")]:
    jobs.append(job(B + "handouts/misc/%s.pdf" % f, "90-原始PDF/15-122/misc/%s.pdf" % f,
                    "15-122", "Fall 2026", LIC, t))
for g in ["questions", "laptop", "terminal", "vim", "vscode", "style", "c0debugging", "autolab",
          "testing", "print", "contracts", "cdebugging", "valgrind", "cprint", "clib"]:
    jobs.append(job(B + "handouts/gts/%s.pdf" % g, "90-原始PDF/15-122/gts/%s.pdf" % g,
                    "15-122", "Fall 2026", LIC, "Guides to Success: %s" % g))
dump("15-122.json", jobs)

# ---------------- 15-213 ----------------
B = "https://www.cs.cmu.edu/~213/"
jobs = []
lectures = ["01-overview", "02-bits-bytes-ints", "03-machine", "04-machine-beta", "05-machine-gamma",
            "06-machine-delta", "07-linking", "08-design-debugging", "09-memory-hierarchy",
            "10-cache-memories", "11-vm-concepts", "12-vm-details", "13-malloc-basic",
            "14-malloc-advanced", "15-optimization", "16-processes", "17-ecf", "18-system-io"]
for i in lectures:
    jobs.append(job(B + "lectures/%s.pdf" % i, "90-原始PDF/15-213/lectures/%s.pdf" % i,
                    "15-213", "Fall 2026", LIC, "讲义 %s" % i))
for i in range(1, 11):
    for k in ["handout", "slides"]:
        jobs.append(job(B + "recitations/rec%02d_%s.pdf" % (i, k),
                        "90-原始PDF/15-213/recitations/rec%02d_%s.pdf" % (i, k),
                        "15-213", "Fall 2026", LIC, "复习课 %02d %s" % (i, k)))
for f, t in [("lab1_slides", "Bootcamp 1 幻灯片"), ("lab1_handout", "Bootcamp 1 讲义"),
             ("lab2_slides", "Bootcamp 2 幻灯片"), ("lab2_handout", "Bootcamp 2 讲义"),
             ("lab3_slides", "Bootcamp 3 幻灯片"), ("lab3_handout", "Bootcamp 3 讲义"),
             ("cprogramming-bootcamp-s23", "C 语言 Bootcamp（2023 春季录制）")]:
    jobs.append(job(B + "bootcamps/%s.pdf" % f, "90-原始PDF/15-213/bootcamps/%s.pdf" % f,
                    "15-213", "Fall 2026", LIC, t))
for a in ["machine-control", "machine-procedures", "machine-advanced"]:
    for suf in ["", "-soln"]:
        jobs.append(job(B + "activities/%s%s.pdf" % (a, suf),
                        "90-原始PDF/15-213/activities/%s%s.pdf" % (a, suf),
                        "15-213", "Fall 2026", LIC, "课堂活动 %s%s" % (a, suf)))
jobs += [
    job(B + "labs/cprogramminglab.pdf", "90-原始PDF/15-213/labs/cprogramminglab.pdf",
        "15-213", "Fall 2026", LIC, "L0 C Programming Lab 说明"),
    job(B + "labs/cprogramminglab-handout.tar", "90-原始PDF/15-213/labs/cprogramminglab-handout.tar",
        "15-213", "Fall 2026", LIC, "L0 C Programming Lab 代码包"),
    job(B + "syllabus/syllabus.pdf", "90-原始PDF/15-213/labs/syllabus.pdf",
        "15-213", "Fall 2026", LIC, "课程大纲"),
    job(B + "recitations/gdbnotes-x86-64.pdf", "90-原始PDF/15-213/recitations/gdbnotes-x86-64.pdf",
        "15-213", "Fall 2026", LIC, "GDB 笔记"),
    job(B + "recitations/x86-cheat-sheet.pdf", "90-原始PDF/15-213/recitations/x86-cheat-sheet.pdf",
        "15-213", "Fall 2026", LIC, "x86-64 速查表"),
    job(B + "recitations/fwunixref.pdf", "90-原始PDF/15-213/recitations/fwunixref.pdf",
        "15-213", "Fall 2026", LIC, "Unix 参考"),
]
dump("15-213.json", jobs)

# ---------------- 15-214 ----------------
B = "https://www.cs.cmu.edu/~aldrich/214/slides/"
jobs = []
files = ["01a-intro.pdf", "01b-orga.pdf", "02-objects.pdf",
         "03 Encapsulation and inheritance.pdf",
         "04 Inheritance, type-checking, and Method dispatch.pdf",
         "05 Object contracts and exceptions.pdf",
         "06 Mutability and Java Potpourri.pdf", "07-design-patterns.pdf",
         "07-design-pattern-notes.pdf", "08-specification.pdf", "08-testing.pdf",
         "09-design-patterns-continued.pdf", "conceptual-modeling.pdf", "design-grasp.pdf",
         "design-information-hiding.pdf", "dsms.pdf", "gui-intro.pdf", "guis-continued.pdf",
         "formal-analysis-part2.pdf", "14 Collections.pdf", "14-frameworks.pdf",
         "18-concurrency-part1.pdf", "19-concurrency-part2.pdf", "20-concurrency-part3.pdf",
         "21-distributed-systems.pdf", "22-distributed-systems-part2.pdf",
         "23-distributed-systems-part3.pdf", "24-staticanalysis.pdf",
         "25-analysis-concurrency.pdf", "26-data-consistency.pdf", "27-history-oo.pdf",
         "28-why-objects.pdf", "28-protocol-programming.pdf", "28-dsls-in-wyvern.pdf",
         "course-review.pdf"]
for f in files:
    local = f.replace(" ", "_")
    jobs.append(job(B + quote(f), "90-原始PDF/15-214/slides/%s" % local,
                    "15-214", "Fall 2013", LIC214, f))
jobs += [
    job("https://www.cs.cmu.edu/~aldrich/214/recitations/recitation1.pdf",
        "90-原始PDF/15-214/notes/recitation1.pdf", "15-214", "Fall 2013", LIC214,
        "Recitation 1 讲义"),
    job("https://www.cs.cmu.edu/~aldrich/214/slides/formal-analysis-notes.txt",
        "90-原始PDF/15-214/notes/formal-analysis-notes.txt", "15-214", "Fall 2013", LIC214,
        "形式化分析笔记（纯文本）"),
    job("https://www.cs.cmu.edu/~aldrich/214/slides/07-design-pattern-notes.txt",
        "90-原始PDF/15-214/notes/07-design-pattern-notes.txt", "15-214", "Fall 2013", LIC214,
        "设计模式笔记（纯文本）"),
]
dump("15-214.json", jobs)

# ---------------- 15-445 ----------------
B = "https://15445.courses.cs.cmu.edu/fall2026/"
jobs = []
slides = ["01-relationalmodel", "02-modernsql", "03-storage1", "04-bufferpool", "05-storage2",
          "06-storage3", "07-hashtables", "08-indexes1", "09-indexes2", "10-indexconcurrency",
          "11-sorting", "12-joins", "13-queryexecution1", "14-queryexecution2",
          "15-optimization1", "16-optimization2", "17-concurrencycontrol", "18-twophaselocking"]
notes = ["01-relationalmodel", "02-modernsql", "03-storage1", "04-bufferpool", "05-storage2",
         "06-storage3", "07-hashtables", "08-indexes1", "09-indexes2", "10-indexconcurrency",
         "11-sorting", "12-joins", "13-queryexecution1", "14-queryexecution2",
         "16-optimization2", "17-concurrencycontrol"]
for s in slides:
    jobs.append(job(B + "slides/%s.pdf" % s, "90-原始PDF/15-445/slides/%s.pdf" % s,
                    "15-445", "Fall 2026", LIC445, "幻灯片 %s" % s))
for n in notes:
    jobs.append(job(B + "notes/%s.pdf" % n, "90-原始PDF/15-445/notes/%s.pdf" % n,
                    "15-445", "Fall 2026", LIC445, "讲义笔记 %s" % n))
for h in ["hw2", "hw3", "hw4", "hw5"]:
    jobs.append(job(B + "files/%s-15445-fall26.pdf" % h,
                    "90-原始PDF/15-445/homework/%s-15445-fall26.pdf" % h,
                    "15-445", "Fall 2026", LIC445, "作业 %s" % h))
dump("15-445.json", jobs)
