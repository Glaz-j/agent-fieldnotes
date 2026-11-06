# 开始之前：第一次用终端和 Python

你可以先看第 1 章的机器人演示，再来这里准备动手。这里不计入 16 章进度；目标是让你知道命令输入到哪里、文件保存在哪里，以及如何判断一次运行是否符合预期。

## 选一个合适的起点

| 你现在的情况 | 从哪里开始 | 做到什么就继续 |
| --- | --- | --- |
| 只想先理解机器人 Agent | [第 1 章](learn/01.html) | 能说出观察、技能、决策、验收各自负责什么 |
| 没用过终端，或分不清 Python 与 JSON | 本页 | 能运行小脚本，并解释下面两个自查题 |
| 会基础 Python，尚未安装实验 | [第 2 章](learn/02.html) | 自检通过，固定脚本生成成功记录 |
| 已跑通前 9 章 | [第 10 章](learn/10.html) | 继续研究记忆，再做双物体毕业任务 |

先完成一个小步骤再向下走，不需要先读完全部教程。本课基础路线不需要实体机器人、GPU、模型账号或付费 API。

## 1. 分清三个地方

**网页**用来读教材和播放演示。**终端**用来告诉计算机运行哪个程序。**文本编辑器**用来打开和修改 `.py`、`.json` 这些纯文本文件。网页上的“复制”只把文字放进剪贴板，还没有运行实验。

macOS 在应用列表中打开“终端”；Windows 打开 PowerShell；Linux 使用系统的终端应用。终端左侧可能显示用户名、路径、`$` 或 `>`，那是提示符，不要把它抄进命令。看到新的提示符，通常表示上一条命令已结束；没有新提示符时先读输出，不要连续重复粘贴。

代码框有两类：标注“在终端运行”的命令逐行粘贴到终端；标注“保存为文件”的代码放进指定文件。标注“预期输出”的文字用来比较，**不需要输入**。

## 2. 先确认 Python，再找对文件夹

在终端运行一条版本检查。macOS / Linux：

```sh
python3 --version
```

Windows：

```powershell
py --version
```

预期看到类似 `Python 3.12.16` 的一行。课程实测 Python 3.12；最后的小版本可以不同。若提示找不到命令，先按 [Python 3.12 官方安装指南](https://docs.python.org/3.12/using/index.html) 选择对应系统安装，再重新打开终端。这里还不安装机器人依赖，第 2 章会建立专用环境。

下载并解压 [实验包](downloads/agent-fieldnotes-lab.zip)。在文件管理器中找到那个直接包含 `lab` 文件夹的位置。终端的“当前目录”就是它查找相对路径的起点。

在终端输入 `cd `，后面接上这个文件夹的完整路径；路径含空格时用英文双引号包住。例如，下面的 `你的用户名` 必须替换，不能照抄：

```sh
cd "/Users/你的用户名/Downloads/agent-fieldnotes-lab"
```

Windows 路径例子：`cd "C:\Users\你的用户名\Downloads\agent-fieldnotes-lab"`。不同解压软件生成的文件夹名字可能不同，以你看到的实际目录为准。

macOS / Linux 用 `pwd` 查看当前目录、`ls` 列出其中的文件；PowerShell 对应 `Get-Location` 和 `Get-ChildItem`。**检查点：列表里直接出现 `lab`。** 如果直接看见 `run.py`，说明进到了 `lab` 里面，运行 `cd ..` 返回外层。

## 3. 写一个不依赖机器人的小程序

在这个外层文件夹新建 `first_check.py`，用代码编辑器或纯文本模式打开。确认文件名不是 `first_check.py.txt`。把下面代码保存进去：

```python
holding = False
distance = 0.03
tolerance = 0.05

def is_finished(is_holding, gap, limit):
    return (not is_holding) and gap <= limit

observation = {"holding": holding, "distance": distance}
print(observation["distance"])
print(is_finished(observation["holding"], observation["distance"], tolerance))

for step in [1, 2, 3]:
    print("check", step)
```

先预测会显示什么，再在终端运行 `python3 first_check.py`（Windows 用 `py first_check.py`）。预期输出：

```text
0.03
True
check 1
check 2
check 3
```

这段小程序用到了后面最常见的几种写法：

| 写法 | 在这个例子里的意思 |
| --- | --- |
| `distance = 0.03` | 把数字保存到变量 `distance`；这里约定单位为米 |
| `def ...` 与 `return` | 定义一个函数，并返回一次判断的结果 |
| `not`、`and`、`<=` | 没有持物，并且距离不大于阈值 |
| `{ "holding": holding, ... }` | 字典：给不同值起名称；用 `[...]` 按名称取值 |
| `[1, 2, 3]` 和 `for` | 列表与循环：对三个编号依次执行下面的语句 |
| 每行前面的四个空格 | 表示哪些语句属于函数或循环，不能随意删掉 |

现在只改 `holding = True`，保存，再运行。预期第二行变为 `False`：仍抓着物体，即使位置已经接近，也不算完成。这个自查只是逻辑练习，真正的仿真验收从第 2 章开始。

**自查题 1：** 恢复 `holding = False`，把 `distance` 改成 `0.08`，第二行会是什么？

<details class="answer"><summary>先预测，再展开参考解释</summary><p><code>False</code>。0.08 米大于 0.05 米，位置条件没有满足；只满足“已放手”还不够。恢复原代码后再继续。</p></details>

如果这些语法还很陌生，可以先完成 [Software Carpentry 的 Python 基础课](https://swcarpentry.github.io/python-novice-inflammation/01-intro.html) 中变量、列表、选择、循环与函数的练习，再回来运行本课小程序。看懂输出比一次记住所有语法更重要。

## 4. Python 代码和 JSON 记录有什么不同

Python 文件告诉程序**如何计算**；JSON 文件保存**本次数据**。下面是手写教学示例，不是运行结果：

```json
{"holding": false, "distance": 0.03, "error": null}
```

在 JSON 中布尔值用小写 `true` / `false`，空值用 `null`，字符串和键用双引号。Python 对应 `True` / `False` / `None`。不要把一整段 JSON 原样当成 Python 程序运行；第 2 章用 `python -m json.tool 文件路径` 阅读真实记录。

**自查题 2：** `"holding": false` 和 `"holding": "false"` 有什么区别？

<details class="answer"><summary>查看解释</summary><p>第一个值是布尔值“否”；第二个是五个字母组成的文本。引号改变了数据类型。机器人程序需要的是明确的布尔判断，而不是一句看起来像判断的文字。</p></details>

## 5. 从报错中找到下一步

| 你看到的现象 | 先做这一步 |
| --- | --- |
| 找不到 `first_check.py` 或 `lab/run.py` | 列出当前目录，确认文件确实在这里；检查文件名和后缀 |
| `SyntaxError` | 查看报错指向的行，检查英文引号、冒号和括号是否完整 |
| `IndentationError` | 检查函数和循环内部的缩进，避免混用 Tab 和空格 |
| `NameError` | 检查变量拼写、大小写，以及是否先赋值再使用 |
| 运行后没有机器人窗口 | 第 2 章默认输出日志；网页视频是录像，不是本机正在运行的窗口 |

遇到卡点时，保存“哪章哪一步、操作系统、完整命令、预期结果、实际输出”。复制文字比只写“运行不了”更容易获得帮助。可使用 [学习卡点反馈表](https://github.com/Glaz-j/agent-fieldnotes/issues/new?template=learner-feedback.yml)；发布前移除密钥和无关个人路径。

## 准备好了，接下来怎么学

能运行小脚本、找到 `lab`、解释两个自查题，就可以进入 [第 1 章](learn/01.html) 理解任务，再按 [第 2 章](learn/02.html) 创建虚拟环境。第 3—5 章补观察、坐标与技能；第 6—9 章把它们连成可恢复的循环。第 8、12 章的图像实验可在渲染可用后补做。

每次学习留下三行笔记：**我原先预测什么 → 实际观察到什么 → 下一次只改变什么**。这份记录会在第 15 章做对照实验时再次用到。
