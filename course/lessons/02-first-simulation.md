# 第 2 章：搭建第一个机器人实验环境

第一次使用终端或 Python？先完成 [新手准备页](../start.html) 的小程序，再回来继续本章。

上一章把系统拆成几个环节。这一章先建立一个能重复启动、读取状态、执行动作并留下记录的环境。后续所有 Agent 改进都建立在同一套实验上；环境不稳定，换提示词也无法解释结果。

这里的网页负责教学与案例浏览，机器人实验在你自己的计算机上运行。你需要一个可用的 Python 和终端：macOS 可打开“终端”，Windows 可打开 PowerShell。下面的命令逐行输入，按回车执行；代码框里的说明文字与边框不需要输入。

## 本章目标

你将安装课程实验包，运行环境自检，读取初始观察，并执行一次固定脚本基线。验收产物是运行命令、环境信息和一次真实生成的运行记录。

## 我们实际使用什么机器人

MuJoCo 是本课程使用的物理仿真程序，负责计算关节和物体在受力后如何运动。我们的场景是一台简化 SCARA：你可以把它看成桌面上两段会转动的手臂，加上一段能上下升降的工具。两个转动关节决定水平位置，滑动关节决定高度，第 4 章会进一步算清楚这个关系。

它不是展厅中的 Panda。教学抓取通过显式约束附着来模拟物体被夹持，不是对指尖摩擦接触的完整建模。因此，本实验适合学习观察、动作接口、闭环和失败恢复，不能用它验证某种真实夹爪的抓取成功率。

MuJoCo 的场景模型描述结构与参数，运行时状态保存关节位置等动态信息。可以把前者理解为“实验装置是什么”，后者理解为“装置此刻处于什么状态”。重置一次任务改变运行状态，不需要重新发明一套机器人。

先看一遍课程基线演示，记住红块、蓝区和末端分别在哪里。观看时数一数：到方块上方、下降、抓取、抬升、横移、下降、释放，共有哪七个阶段？

<!-- course-demo: course-baseline -->

这里的基线就是用来比较的最简单参考做法，按预先写好的顺序执行。稍后本机运行的是同一套实验代码；命令默认输出文字和文件，不会自动弹出一个机器人窗口。

## 第一步：取得课程代码

先下载 [轻量课程实验包](../downloads/agent-fieldnotes-lab.zip) 并解压。用终端的 `cd` 命令进入解压后的外层文件夹：输入 `cd "你的解压文件夹路径"`，将引号里的文字替换成实际路径。我们把“能直接看到 `lab/` 文件夹的这一层”叫作实验根目录，它应该具有下面的结构：

```text
实验根目录/       ← 终端停在这里
└── lab/
    ├── run.py
    ├── scene.xml
    └── requirements.txt
```

`run.py` 是命令入口，`scene.xml` 描述机器人与场景，`requirements.txt` 列出 Python 依赖。轻量包已经包含这些内容，无需先下载展厅录像。

如果希望同时取得完整网站与案例媒体，也可以选择克隆仓库；完整资源约数百 MB：

```sh
git clone https://github.com/Glaz-j/agent-fieldnotes.git
cd agent-fieldnotes
```

下载轻量包与克隆完整仓库是两种取得代码的方法，选择一种即可。后面提到“根目录”均指包含 `lab/` 的这一层；命令中的 `lab/run.py` 就是从这里找到 `lab` 内的入口文件。

建议使用 Python 3.12，与课程实测环境保持接近。macOS / Linux 可先运行 `python3 --version`，Windows 运行 `py --version`；若找不到命令，先按 [Python 官方安装说明](https://docs.python.org/3.12/using/index.html) 安装，再重新打开终端。

接下来建立“虚拟环境”：它是这个实验专用的 Python 依赖目录，避免不同项目的软件包混在一起。下面三行分别创建环境、在当前终端激活它、安装课程依赖。若装了多个 Python，可在创建这一步用 `python3.12` 或 Windows 的 `py -3.12` 明确选择 3.12。macOS / Linux 使用：

```sh
python3 -m venv lab/.venv
source lab/.venv/bin/activate
python -m pip install -r lab/requirements.txt
```

Windows PowerShell 使用：

```powershell
py -m venv lab/.venv
.\lab\.venv\Scripts\Activate.ps1
python -m pip install -r lab/requirements.txt
```

安装成功后，后面的 `python` 就表示这个环境里的解释器。新开终端时，需要重新进入实验根目录并执行激活那一行；不用每次重新创建环境或安装依赖。

若 PowerShell 不允许执行激活脚本，可以把后续命令开头的 `python` 换成 `.\lab\.venv\Scripts\python.exe`，安装依赖时也同样替换。macOS / Linux 对应路径是 `lab/.venv/bin/python`。这会直接选择环境，不需要修改全局策略。

## 第二步：先做环境自检

先确认两个容易混淆的位置：终端当前所在的文件夹，以及实际运行的 Python。下面两行只读信息，不会移动文件：

```sh
python -c "from pathlib import Path; print(Path.cwd()); print(Path('lab/run.py').is_file())"
python -c "import sys; print(sys.executable)"
```

第一行先打印当前目录，再打印 `True` 或 `False`。这里应是 `True`，表示从当前位置确实能找到 `lab/run.py`；若是 `False`，先用 `cd` 回到包含 `lab/` 的那层。第二行的路径应指向本实验的 `lab/.venv` 内部。`python -c` 的意思是“执行引号里的这一小段 Python”，不必为这两个检查另外保存文件。

两个位置确认后，再检查机器人环境：

```sh
python lab/run.py doctor
```

自检的意义是确认程序正在使用预期解释器，MuJoCo 能被导入，教学场景能够建立。先读完整输出，再决定下一步。不要在依赖导入失败时继续尝试模型接口：这两个问题发生在完全不同的层。

输出是一组带名称的值，其中 `physics: "ok"` 表示物理场景可用，`render: "ok"` 表示还能生成图像。`render` 若是 `unavailable: ...`，先保存错误信息；本章的状态与基线实验仍可继续，第 8 章图像实验则需要先解决渲染问题。

把 Python 与 MuJoCo 版本、操作系统以及自检结果保存到学习笔记。使用相同版本不意味着所有计算机都完全一致，但这些信息能显著缩小排查范围。

## 第三步：读取一次观察

**先预测：** 刚启动、还没有任何搬运动作时，“正在持物”和“任务完成”各应该是什么？在笔记中先写下两个答案，再执行命令。

```sh
python lab/run.py observe
```

输出采用 JSON 格式：用名称对应一个值，例如 `"holding": false` 表示当前没有持物，`"tool_xyz": [...]` 保存末端位置。`true` 是“是”，`false` 是“否”。初始场景的 `task` 中应看到 `"success": false`，因为方块还没搬到目标。

第 3 章会逐项解释字段。本章先确认程序能读出 `robot`、`scene` 与 `task` 三组信息，不需要一次理解全部坐标。

观察并不是让机器人自动决策。读取到一个坐标，也不等于它经过相机识别。如果程序直接读取仿真内部位置，应将其记作精确状态输入。

## 第四步：运行固定脚本基线

```sh
python lab/run.py baseline --seed 7 --out runs/baseline
```

这里的基线采用预先写好的动作顺序，不调用语言模型。命令中 `--seed 7` 使用编号 7 的随机初始化，便于下次重建相同起点；`--out runs/baseline` 把记录保存在根目录下的 `runs/baseline`。程序会创建这个输出目录，不需要你预先建好。

运行结束后，检查终端报告与 `runs/baseline` 中生成的 `events.jsonl`、`summary.json`。前者记录每次技能调用，后者汇总本次任务。课程基线在任务成功时退出码为 0，失败时为 2；仍要阅读汇总中的 `success`、`error` 和最终状态，才能解释成功或失败的原因。

用文本编辑器打开文件，或者在同一终端运行下面的命令，把汇总排版后显示出来：

```sh
python -m json.tool runs/baseline/summary.json
```

正常的种子 7 结果应包含 `"mode": "baseline"`、`"steps": 7`、`"model_calls": 0` 和 `"success": true`。其中 `steps` 数的是七次技能调用，不是七个物理仿真步；`error: null` 表示这里没有记录到程序异常，`null` 是 JSON 的空值。

## 实验：重置是否真的可重复

先用 `python lab/run.py observe --seed 7` 单独查看并保存初始状态。基线的事件日志从第一次技能执行后的状态开始，不能把第一条事件当成动作前的初始观察。

使用相同种子再运行一次，然后改变种子另存第三次实验：

```sh
python lab/run.py baseline --seed 7 --out runs/baseline-repeat
python lab/run.py baseline --seed 8 --out runs/baseline-seed8
```

先比较两次种子 7 的动作顺序、每步反馈与最终验收结果。若同一种子下结果不同，记录差异出现在哪一步。

再比较种子 8：随机初始化变化后，哪些坐标变化，哪些机器人结构保持不变？这个比较能帮助你区分场景参数、初始化状态和控制逻辑。每次命令都从新场景开始，不会沿用上一条命令留下的位置。

先分别保存结果再比较，避免把两次输出写进同一目录后失去来源。

**检查点：** 完成基线后，再运行 `python lab/run.py observe --seed 7`，预期仍是 `holding: false`、`task.success: false`，方块回到初始位置。这不是上一回合的成功记录丢失了，而是新命令创建了新场景。上一回合的证据仍在 `runs/baseline/`。不同种子会改变初始方块位置；连杆长度和蓝区位置在这项实验里保持不变。若只想比较初始位置，应分别运行两个种子的 `observe`，不要把搬运后的终点误当起点。

## 本章验收

你应该能够从一个新终端进入仓库、激活环境、运行自检并执行基线。提交一份简短记录，包含实际命令、版本、种子、结果目录以及你对结果的判断。发生失败时，也保留完整报告并解释它属于安装、场景加载、技能执行还是任务验收问题。

能稳定运行这条离线基线，就是后续学习的起点。下一章会把现在看到的 JSON 拆开，弄清每个字段从哪里来、能够支持什么判断。

## 常见错误与排查

`No module named mujoco` 通常表示依赖装到了另一个解释器。先比较 `python` 与 `python -m pip` 使用的环境，再安装依赖。

“找不到 lab/run.py”通常是工作目录不对。先确认当前目录下存在 `lab/`。

图形或离屏渲染错误与物理仿真错误不同。先检查环境自检和纯状态操作，再处理显示驱动或渲染配置；不要把渲染失败描述成模型决策失败。MuJoCo 官方文档还说明了 macOS 被动查看器的特殊启动要求，只有使用对应查看器时才适用。

## 练习与参考

基础题：用两个种子分别建立记录目录，写出两项相同和两项不同的信息。挑战题：写一个你自己的实验记录模板，使别人仅凭模板就知道如何重新运行你的实验。

- [MuJoCo Python 安装与使用](https://mujoco.readthedocs.io/en/stable/python.html)
- [Python 虚拟环境官方文档](https://docs.python.org/3/library/venv.html)
- [课程实验包](https://github.com/Glaz-j/agent-fieldnotes/tree/main/lab)
