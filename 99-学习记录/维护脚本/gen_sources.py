# -*- coding: utf-8 -*-
"""从 download-manifest.json 生成 03-资料来源与版权记录.md"""
import json, os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAN = os.path.join(ROOT, '99-学习记录', 'download-manifest.json')
OUT = os.path.join(ROOT, '03-资料来源与版权记录.md')

COURSE_META = {
    '15-122': dict(
        name='Principles of Imperative Computation（命令式计算原理）',
        site='https://www.cs.cmu.edu/~15122-archive/f26/',
        sem='Fall 2026',
        lic='课程网站未标注开放许可（无 CC 声明）。按「仅作个人学习存档、不转载分发」处理。',
    ),
    '15-213': dict(
        name='Introduction to Computer Systems（计算机系统导论，含 14-513/15-513）',
        site='https://www.cs.cmu.edu/~213/',
        sem='Fall 2026',
        lic='课程网站未标注开放许可。课件中引用的 CSAPP 图表版权属 Pearson，按「仅作个人学习存档」处理。',
    ),
    '15-214': dict(
        name='Objects, Design, and Concurrency（对象、设计与并发）',
        site='https://www.cs.cmu.edu/~aldrich/214/',
        sem='Fall 2013（历史学期存档）',
        lic='课程网站标注 CC BY-SA 3.0，但该声明在页面上主要针对 toad 图片；其余讲义未逐份标注许可，保守按「仅作个人学习存档」处理。',
    ),
    '15-445': dict(
        name='Database Systems（数据库系统，含 15-645）',
        site='https://15445.courses.cs.cmu.edu/fall2026/',
        sem='Fall 2026',
        lic='课程网站未标注开放许可。幻灯片中引用的教材图表版权属 McGraw-Hill，按「仅作个人学习存档」处理。',
    ),
}

def fmt_size(n):
    if n >= 1048576:
        return '%.1f MB' % (n / 1048576)
    if n >= 1024:
        return '%.1f KB' % (n / 1024)
    return '%d B' % n

def main():
    data = json.load(open(MAN, encoding='utf-8'))
    items = data['items']
    ok = [i for i in items if i.get('status') == 200]
    bad = [i for i in items if i.get('status') != 200]

    L = []
    a = L.append
    a('---')
    a('course: 通用')
    a('course_name: 资料来源与版权记录')
    a('semester: 跨课程')
    a('language: zh-CN')
    a('status: draft')
    a('tags:')
    a('  - 来源记录')
    a('  - 版权')
    a('  - 许可')
    a('---')
    a('')
    a('# 资料来源与版权记录')
    a('')
    a('本文件逐条记录知识库内每一份原始材料的**来源 URL、所属课程与学期、下载日期、许可状态**，用于长期追溯。')
    a('')
    a('## 使用与合规声明')
    a('')
    a('1. 本知识库中所有原始 PDF、代码包、纯文本均**仅从公开可访问的课程官网直接下载**，未使用任何登录、付费、破解或绕过访问控制的手段。')
    a('2. 未下载任何**答案（solution/answer key）、评分测试、学生作业提交、教师解答手册、整本教材或盗版书**。')
    a('3. 未下载任何 **YouTube 视频文件**。视频仅以链接形式记录，见各课程笔记第 9 节。')
    a('4. 未抓取受 Autolab / Gradescope / Ed / Piazza 权限保护的材料，仅在笔记中标注「需要课程权限」。')
    a('5. 原始 PDF 一律**保留原文件名与原内容**，未做任何替换或改写；中文笔记是独立撰写的二次材料，与原始材料分目录存放。')
    a('6. 所有材料**仅作个人学习存档**，不再分发、不用于商业用途。若版权方要求，应立即删除对应文件。')
    a('7. 若某份材料官网未明确标注开放许可，本知识库一律按「未授权转载」处理，只做本地个人学习使用。')
    a('')
    a('## 学期与版本说明（重要）')
    a('')
    a('| 课程 | 本知识库采用的学期 | 说明 |')
    a('|---|---|---|')
    a('| 15-122 | Fall 2026 | 官网当前学期存档页 `~15122-archive/f26/` |')
    a('| 15-213 | Fall 2026 | 官网当前学期 |')
    a('| 15-214 | **Fall 2013** | 官网公开页面停留在 2013 年，属历史学期存档，**不是 2026 年课程** |')
    a('| 15-445 | Fall 2026 | 官网当前学期；视频使用 Fall 2025 公开录像（见下） |')
    a('')
    a('**不同学期材料绝不混用。** 同一门课的所有讲义、课表、笔记均来自上表所列的同一学期。')
    a('')
    a('## 视频来源说明')
    a('')
    a('- 15-122 / 15-213 / 15-214：**未找到官方公开录像**，笔记第 9 节据实写明。')
    a('- 15-445 Fall 2026：FAQ Q11 原文写明 *"the Fall 2026 lectures will be recorded but will only be available to CMU students. Non-CMU students should watch the Fall 2025 lectures on YouTube."*')
    a('  - 因此非 CMU 学习者使用 **Fall 2025 公开视频**：`https://www.youtube.com/playlist?list=PLSE8ODhjZXjYMAgsGH-GtY5rJYZ6zjsd5`')
    a('  - 2025 与 2026 的讲次编号不同（2025 第 12 讲为 Joins，2026 因第 12 讲停课而顺延为第 13 讲），本知识库**按主题映射**，不按编号硬套。')
    a('  - 所有 15-445 笔记中出现的视频链接均标注年份为 **2025**，与 Fall 2026 的讲义材料明确区分。')
    a('- 未核实具体时间戳，因此**所有笔记均不标注视频时间戳**，避免编造。')
    a('')
    a('## 下载统计')
    a('')
    a('| 课程 | 成功下载 | 失败/缺失 | 总字节 |')
    a('|---|---|---|---|')
    for c in ['15-122', '15-213', '15-214', '15-445']:
        good = [i for i in ok if i['course'] == c]
        bd = [i for i in bad if i['course'] == c]
        a('| %s | %d | %d | %s |' % (c, len(good), len(bd), fmt_size(sum(i['size'] for i in good))))
    a('| **合计** | **%d** | **%d** | **%s** |' % (len(ok), len(bad), fmt_size(sum(i['size'] for i in ok))))
    a('')
    a('下载时间：2026-11-10（本机时间）。全部文件已计算 SHA-256，见 `99-学习记录/download-manifest.json`。')
    a('')

    for c in ['15-122', '15-213', '15-214', '15-445']:
        meta = COURSE_META[c]
        good = sorted([i for i in ok if i['course'] == c], key=lambda x: x['local_path'])
        a('## %s — %s' % (c, meta['name']))
        a('')
        a('- 课程官网：%s' % meta['site'])
        a('- 学期：%s' % meta['sem'])
        a('- 许可状态：%s' % meta['lic'])
        a('- 本课程已下载文件数：%d' % len(good))
        a('')
        a('| # | 本地路径 | 文件大小 | 下载日期 | 来源 URL |')
        a('|---|---|---|---|---|')
        for n, i in enumerate(good, 1):
            rel = i['local_path'].replace('\\', '/')
            a('| %d | `%s` | %s | %s | <%s> |' % (
                n, rel, fmt_size(i['size']), i['fetched_at'][:10], i['url']))
        a('')

        bd = [i for i in bad if i['course'] == c]
        if bd:
            a('### 未能获取的材料（%d 项）' % len(bd))
            a('')
            a('| 来源 URL | HTTP 状态 | 原因与处理 |')
            a('|---|---|---|')
            for i in bd:
                a('| <%s> | %s | 服务器返回 %s，未做任何绕过尝试；已在笔记中标注该材料缺失。 |' % (
                    i['url'], i['status'], i['status']))
            a('')

    a('## 明确未下载的材料类别')
    a('')
    a('| 类别 | 涉及课程 | 原因 |')
    a('|---|---|---|')
    a('| Autolab / Gradescope 上的 lab 与作业 | 15-122、15-213、15-445 | 需要 CMU 课程账号，属访问控制范围，不绕过 |')
    a('| Ed / Piazza 讨论区 | 四门课 | 需登录，且内容含学生隐私 |')
    a('| 考试卷与答案、作业解答 | 四门课 | 明确排除：不下载答案、评分测试、教师解答 |')
    a('| 学生作业提交 | 四门课 | 含个人隐私与学术诚信风险 |')
    a('| CSAPP 等教材整本 PDF | 15-213、15-445 | 受版权保护，不下载盗版书；只记录官方教材站点链接 |')
    a('| YouTube 视频文件与字幕 | 15-445 | 不下载视频；字幕未确认公开许可，故不抓取 |')
    a('| Google Calendar ICS | 15-122、15-213 | 连接超时，无法获取；课表信息已从 HTML 页面取得 |')
    a('| GitHub 上的社区翻译仓库 | 15-213 | 连接超时/限流，未取到；且属第三方材料，不作为主来源 |')
    a('')

    txt = '\n'.join(L) + '\n'
    with open(OUT, 'w', encoding='utf-8', newline='\n') as f:
        f.write(txt)
    print('wrote', OUT, len(txt), 'chars', len(L), 'lines')

if __name__ == '__main__':
    main()
