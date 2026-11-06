#!/usr/bin/env python3
"""Build the Markdown lessons and course entry into GitHub Pages /docs."""
from pathlib import Path
import html
import re
import zipfile
import markdown

ROOT = Path(__file__).resolve().parent
DOCS = ROOT / 'docs'
REPO = 'https://github.com/Glaz-j/agent-fieldnotes'
CHAPTERS = [
    ('拆解一个机器人 Agent', '任务、观察、决策与执行分别由谁负责', '01-robot-agent.md'),
    ('运行第一个仿真环境', '安装 MuJoCo，让机械臂完成一次任务', '02-first-simulation.md'),
    ('机器人究竟知道什么', '区分物理状态、传感器观察与隐藏信息', '03-observation-state.md'),
    ('从坐标到机械臂运动', '理解坐标系、逆运动学与控制器', '04-coordinates-motion.md'),
    ('把动作封装成技能', '为移动、抓取与放置定义可检查的接口', '05-robot-skills.md'),
    ('第一个机器人 Agent 循环', '观察、行动、检查，再决定下一步', '06-agent-loop.md'),
    ('把语言变成可检查的目标', '处理指令、歧义与任务完成条件', '07-checkable-goals.md'),
    ('从 RGB 图像估计位置', '用受控颜色定位理解像素、坐标与感知误差', '08-controlled-vision.md'),
    ('执行验证与失败恢复', '面对抓取失败与目标移动，重新组织行动', '09-verification-recovery.md'),
    ('让任务历史成为可用的记忆', '用完成证据记录进度，避免重复执行', '10-task-memory.md'),
    ('会更新的空间记忆', '给位置加上时间与来源，及时修正过期信息', '11-spatial-memory.md'),
    ('主动观察：为行动获取信息', '移动机械臂解除遮挡，比较观察前后的变化', '12-active-perception.md'),
    ('用程序表达机器人计划', '组合技能、条件和预算，执行可检查的计划', '13-program-planning.md'),
    ('把学习技能接入 Agent', '训练一个局部运动技能，理解策略接口与分布边界', '14-learned-skills.md'),
    ('设计可比较的机器人实验', '匹配条件、做消融，用完整记录解释结果', '15-evaluation.md'),
    ('毕业项目：桌面搬运助手', '在同一场景中搬运两个物体，并应对执行中的变化', '16-capstone.md'),
]
CHAPTER_COUNT = len(CHAPTERS)
GROUPS = [
    (1, 5, '机器人基础', '让机器人可靠地动起来'),
    (6, 9, 'Agent 闭环', '让任务形成闭环'),
    (10, 12, '记忆与观察', '让经验和观察真正有用'),
    (13, 16, '整合与评测', '组合能力，完成一个系统'),
]

def chapter_group(number):
    return next(label for start, end, label, _ in GROUPS if start <= number <= end)


def roadmap():
    return ''.join(f'<div><h3>{start:02}—{end:02} / {heading}</h3>{chapter_links(start,end)}</div>' for start,end,_,heading in GROUPS)

def topbar(prefix=''):
    return f'''<a class="skip" href="#main">跳到正文</a><header class="topbar"><a class="brand" href="{prefix}index.html"><b>af</b><span>Agent Fieldnotes<small>机器人 Agent · 从理解到动手</small></span></a><nav aria-label="主导航"><a href="{prefix}index.html#curriculum">学习路线</a><a href="{prefix}gallery.html">实验案例</a><a class="repo" href="{REPO}">GitHub ↗</a></nav></header>'''

def footer(prefix=''):
    return f'''<footer class="footer"><span>Agent Fieldnotes · 在实验中学习机器人 Agent</span><span><a href="{prefix}attributions.html">案例来源与许可</a> · <a href="{REPO}/issues">问题与勘误</a> · <a href="https://glazwu.cn/zhaoye/">关于作者</a></span></footer>'''

def page(title, body, prefix='', description='通过十六章循序渐进的教程和可运行的 MuJoCo 实验，学习机器人 Agent 的感知、记忆、技能、决策与评测。'):
    return f'''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="{html.escape(description, quote=True)}"><meta name="theme-color" content="#f3f4ee"><title>{html.escape(title)} · Agent Fieldnotes</title><link rel="stylesheet" href="{prefix}course.css?v=course16"><script defer src="{prefix}course.js?v=course16"></script></head><body data-lesson-count="{CHAPTER_COUNT}">{topbar(prefix)}{body}{footer(prefix)}</body></html>\n'''

def chapter_links(start, end):
    return ''.join(f'<a class="chapter-row" data-chapter="{i}" href="learn/{i:02}.html"><span class="chapter-num">{i:02}</span><span class="chapter-name">{html.escape(CHAPTERS[i-1][0])}<small>{html.escape(CHAPTERS[i-1][1])}</small></span><span class="arrow" aria-hidden="true">↗</span></a>' for i in range(start, end+1))

def build_home():
    body = f'''<main id="main" class="wrap">
<section class="hero"><div><span class="label">一条从 Python 到机器人决策的学习路线</span><h1>动手构建<br>机器人 Agent</h1><p class="intro">从一次抓取开始，学会让机器人理解任务、调用技能、检查结果，并在失败后继续行动。</p><div class="actions"><a class="primary" href="learn/01.html">开始第 1 章 →</a><a class="secondary" href="downloads/agent-fieldnotes-lab.zip" download>下载教学实验包 ↓</a></div><p class="small">16 章循序渐进 · 本地仿真实验 · 无需实体机器人</p></div>
<figure><video controls playsinline preload="metadata" poster="media/mems-target-shift-libero-three-t00.jpg" aria-label="已有展厅案例：目标碗移动后的机器人任务轨迹"><source src="media/mems-target-shift-libero-three-t00.mp4" type="video/mp4"></video><figcaption><strong>如果目标突然移动，机器人该怎么办？</strong>先带着这个问题学习，再回到 MemS 案例看它如何处理变化。视频来自原展厅；教学实验从更小的任务起步。<br><a href="gallery.html#demo-mems-target-shift-libero-three">查看完整案例与来源 ↗</a></figcaption></figure></section>
<div class="course-band"><div><strong>你需要会什么</strong><p>基础 Python、终端操作、简单向量运算。</p></div><div><strong>你将亲手完成什么</strong><p>运行机械臂，构建技能接口与可恢复的任务循环。</p></div><div><strong>实验从哪里开始</strong><p>独立的简化 MuJoCo 环境；先理解，再接入模型。</p></div></div>
<section class="section" id="curriculum"><span class="label">LEARNING PATH / 学习路线</span><div class="section-lead"><h2>每一章，解决一个具体问题</h2><p>按顺序完成前置知识，再把观察、技能与决策连起来。每章都有动手步骤、验收标准、故障排查和延伸阅读。</p></div><p class="progress-note"><span id="progress-count">0 / {CHAPTER_COUNT} 章已完成</span> · 进度保存在当前浏览器，可随时取消勾选。</p><div class="roadmap">{roadmap()}</div><div class="lab-note"><strong>两条动手入口</strong><br>第一次接触机器人，从第 1 章开始；已经跑通基础实验，从 <a href="learn/10.html">第 10 章的任务记忆</a> 继续。各章明确区分规则、真实模型调用、受控视觉与学习技能，实验不需要下载大模型权重。</div></section>
<section class="section" id="cases"><span class="label">FIELD NOTES / 从真实轨迹提问</span><h2>原来的展厅，成为课堂里的案例库</h2><p class="section-lead">不要只看机器人是否做完。尝试找出：它知道什么、何时决策、哪里出错，以及什么证据说明任务完成。案例与教学实验分开标注，保留各自的实现条件。</p><div class="cases">
<article class="case"><a href="gallery.html#demo-mems-target-shift-libero-three"><img src="media/mems-target-shift-libero-three-t00.jpg" alt="MemS 仿真机械臂与桌面上的容器" loading="lazy"></a><h3>目标移动后，旧计划还有效吗？</h3><p>从空间记忆案例，理解观察的时效性，以及为什么执行之后还要检查。</p><div class="case-links"><a href="learn/11.html">先学第 11 章 →</a><a href="gallery.html#demo-mems-target-shift-libero-three">打开案例 ↗</a></div></article>
<article class="case"><a href="gallery.html#demo-pyrualean-astra-cells-20261028"><img src="media/pyrualean-object2-seed4-20261028-a01.jpg" alt="PyRUA 仿真任务中的机械臂与目标物体" loading="lazy"></a><h3>模型生成代码，就能控制机器人吗？</h3><p>把程序、技能与底层控制分开看，追踪决策怎样变成一次实际动作。</p><div class="case-links"><a href="learn/13.html">先学第 13 章 →</a><a href="gallery.html#demo-pyrualean-astra-cells-20261028">打开案例 ↗</a></div></article>
<article class="case"><a href="gallery.html#demo-robomme-pick-count"><img src="media/robomme-pick-count-test0.png" alt="RoboMME 计数抓取任务的仿真桌面" loading="lazy"></a><h3>怎么知道“做够了”，可以停止？</h3><p>把自然语言要求变成明确的完成条件，区分动作执行与任务成功。</p><div class="case-links"><a href="learn/10.html">先学第 10 章 →</a><a href="gallery.html#demo-robomme-pick-count">打开案例 ↗</a></div></article>
</div><div class="actions"><a class="secondary" href="gallery.html">浏览全部实验案例 →</a><a class="secondary" href="experiments.html">查看原始实验档案 →</a></div></section>
<section class="section"><div class="starter"><div><span class="label">HANDS ON / 从一个最小实验开始</span><h3>让第一次运行保持简单</h3><p>下载并解压实验包，在解压目录创建 Python 环境。第 2 章包含完整安装、环境检查与排错说明。</p><p>机械臂采用简化 SCARA 结构，抓取使用显式附着约束。它用来讲清任务逻辑，不代表真实夹爪的摩擦抓取能力。</p><a class="secondary" href="learn/02.html">查看安装与第一轮实验 →</a></div><pre><code>python -m pip install -r lab/requirements.txt
python lab/run.py doctor
python lab/run.py baseline
python lab/run.py agent --mode scripted</code></pre></div></section>
</main>'''
    (DOCS/'index.html').write_text(page('动手构建机器人 Agent',body),encoding='utf-8')

def build_lessons():
    output = DOCS/'learn'
    output.mkdir(exist_ok=True)
    for number,(title,subtitle,filename) in enumerate(CHAPTERS,1):
        # Authors may choose a more descriptive slug; the chapter number is stable.
        matches = sorted((ROOT/'course/lessons').glob(f'{number:02}-*.md'))
        if len(matches) != 1:
            raise ValueError(f'Chapter {number} needs exactly one source, found {matches}')
        source = matches[0]
        text = source.read_text(encoding='utf-8')
        text = re.sub(r'^# [^\n]+\n', '', text, count=1)
        md = markdown.Markdown(extensions=['fenced_code','tables','toc'], extension_configs={'toc':{'toc_depth':'2-3'}})
        article = md.convert(text)
        nav = ''
        for i,(name,_,_) in enumerate(CHAPTERS,1):
            if i in {g[0] for g in GROUPS}: nav += '<div class="nav-group">'+chapter_group(i)+'</div>'
            nav += f'<a href="{i:02}.html"'+(' aria-current="page"' if i==number else '')+f'>{i:02} · {name}</a>'
        prev = f'<a rel="prev" href="{number-1:02}.html">← 上一章</a>' if number>1 else '<a href="../index.html">← 学习路线</a>'
        nxt = f'<a rel="next" href="{number+1:02}.html">下一章 →</a>' if number<CHAPTER_COUNT else '<a href="../gallery.html">带着问题看案例 →</a>'
        body = f'''<main id="main" class="lesson-layout"><aside class="course-nav" aria-label="课程目录"><details open><summary>课程目录 · {CHAPTER_COUNT} 章</summary><nav>{nav}<div class="nav-group">继续动手</div><a href="../downloads/agent-fieldnotes-lab.zip" download>下载教学实验包 ↓</a><a href="../gallery.html">实验案例库 ↗</a></nav></details></aside><div class="reading"><header><div class="label">第 {number:02} 章 / {chapter_group(number)}</div><h1>{title}</h1><p>{subtitle}</p><div class="lesson-meta">讲解 · 动手实验 · 验收检查 · 练习</div></header><details class="toc-box"><summary>本章内容</summary>{md.toc}</details><article>{article}</article><div class="lab-note">本课程实验使用独立的简化教学环境。展厅链接为阅读案例，不表示实验包复现了该案例的机器人、模型或论文结果。<br><a href="{REPO}/blob/main/{source.relative_to(ROOT).as_posix()}">查看本章源文件</a> · <a href="{REPO}/blob/main/lab/{'GUIDE.md' if number<=9 else 'ADVANCED_GUIDE.md'}">查看实验说明</a></div><div class="lesson-bottom"><label class="finish-label"><input type="checkbox" id="lesson-complete" data-lesson="{number}">我已完成本章学习与验收</label><p class="progress-note" id="progress-status" role="status">学习进度仅保存在当前浏览器。</p><nav class="pager" aria-label="章节翻页">{prev}{nxt}</nav></div></div></main>'''
        (output/f'{number:02}.html').write_text(page(title,body,'../',subtitle),encoding='utf-8')

def build_download():
    output = DOCS/'downloads'
    output.mkdir(exist_ok=True)
    files = [p for p in (ROOT/'lab').iterdir() if p.is_file() and (p.suffix in {'.py','.xml','.txt','.md'} or p.name == 'example-program.json')]
    if not {'run.py','scene.xml','requirements.txt','GUIDE.md','advanced.py','ADVANCED_GUIDE.md','capstone.xml','example-program.json'} <= {p.name for p in files}:
        raise ValueError('Teaching lab source is incomplete')
    # Fixed timestamps make the download reproducible.
    with zipfile.ZipFile(output/'agent-fieldnotes-lab.zip','w',compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            entry = zipfile.ZipInfo('lab/'+path.name, date_time=(2026,11,6,0,0,0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry,path.read_bytes())

if __name__ == '__main__':
    build_lessons()
    build_download()
    build_home()
    print(f'Built {CHAPTER_COUNT} lessons, course homepage and teaching lab download.')
