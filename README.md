# Agent Fieldnotes · 动手构建机器人 Agent

从 Python 和一次桌面搬运任务开始，学习机器人 Agent 的观察、技能、决策、任务验收与失败恢复。首期包含九章中文教程、独立的 MuJoCo 教学实验包，以及原有机器人探索展厅的案例材料。

- [开始学习](https://glaz-j.github.io/agent-fieldnotes/)
- [下载轻量教学实验包](https://glaz-j.github.io/agent-fieldnotes/downloads/agent-fieldnotes-lab.zip)
- [浏览实验案例库](https://glaz-j.github.io/agent-fieldnotes/gallery.html)

## 学习内容

1. 拆解一个机器人 Agent
2. 运行第一个仿真环境
3. 机器人究竟知道什么
4. 从坐标到机械臂运动
5. 把动作封装成技能
6. 第一个机器人 Agent 循环
7. 把语言变成可检查的目标
8. 从 RGB 图像估计位置
9. 执行验证与失败恢复

第 10—16 章为后续规划，尚未开放正文。每章包括概念解释、实验步骤、验收、排错、练习与原始参考资料。进度保存在读者浏览器中。

## 运行教学实验

推荐下载上面的轻量实验包并解压。完整仓库含较多展厅视频，学习实验不需要下载它们。在包含 `lab/` 的目录运行：

```sh
python3 -m venv lab/.venv
source lab/.venv/bin/activate
python -m pip install -r lab/requirements.txt
python lab/run.py doctor
python lab/run.py baseline --seed 7 --out runs/baseline
python lab/run.py agent --mode scripted --seed 7 --out runs/closed-loop
```

Windows、视觉渲染、扰动实验、在线模型配置与结果解释见 [实验说明](lab/GUIDE.md) 和 [第 2 章](course/lessons/02-first-simulation.md)。

实验使用简化 SCARA 机械臂和显式抓取附着约束。`scripted` 是确定性状态反馈控制器，模型调用次数为零；`llm` 才调用用户配置的模型工具接口。RGB 颜色定位是独立视觉练习，尚未构成纯视觉动作闭环。这些边界在教材和日志中均明确标注。

初始发布在 macOS ARM、Python 3.12、MuJoCo 3.3.7 上验证离线物理、渲染和扰动实验。在线模型模式没有真实服务实测结果，不提供在线成功率。详细检查记录见 [实验说明](lab/GUIDE.md)。

## 维护课程与网页

| 路径 | 用途 |
| --- | --- |
| `course/lessons/` | 九章 Markdown 教材源文件 |
| `lab/` | 教学仿真代码、场景、依赖与测试 |
| `build_course.py` | 生成课程网页与可下载实验包 |
| `docs/learn/` | 生成的课程阅读页 |
| `docs/index.html` | 生成的课程首页 |
| `docs/gallery.html` | 原展厅，新增章节关联 |
| `docs/data/`、`docs/media/` | 原有案例记录与视频图像 |

修改教材或实验后重新构建，并将源文件与生成产物一并提交：

```sh
python3 -m venv .course-venv
.course-venv/bin/python -m pip install -r course-requirements.txt
.course-venv/bin/python build_course.py
python3 -m http.server 4330 --directory docs --bind 127.0.0.1
```

GitHub Pages 从 `main` 分支的 `/docs` 发布，网站没有模型密钥或服务端调用。旧的首页 `#demo-…` 分享链接会跳转到原案例，实验总览也指向案例库。

## 案例范围与来源

原展厅保留精选页面、页面引用的图像与录像、技术路线解读和上游署名。完整研究日志、原始模型请求、凭据、权重与数据集未包含。案例中的在线决策、生成代码、预训练策略和经典控制沿用各自标注，不作为统一条件的基准排名。

课程中的展厅链接用于分析任务轨迹，不意味着教学实验包复现了对应论文或系统。课程组织参考 [Datawhale《动手学具身智能》](https://datawhalechina.github.io/dive-into-embodied-ai/) 的循序渐进方式；正文和教学实验独立编写，具体知识引用见各章。

第三方案例、视频与资产来源见 [来源与许可](docs/attributions.html) 和 [署名索引](docs/data/attribution-licenses.json)。本仓库不对第三方材料重新授权。
