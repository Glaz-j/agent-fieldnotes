# 第 7 章：把自然语言变成可检查的目标

第 6 章完成了一个动作循环，但它执行的任务始终是“红块到蓝区”。现在看循环之前的一步：用户说什么，程序才允许开始？再看循环之后的一步：依据什么判断已经完成？

前置要求：能运行第 6 章 `scripted` 模式并读懂日志。本章主线完全离线。末尾的真实模型接入是选学，没有密钥也能完成本章及后续课程。

## 本章目标：分开指令、目标、计划与验收

以“把红色方块放到蓝色区域”为例，四个概念分别是：

| 概念 | 具体例子 | 它回答什么 |
| --- | --- | --- |
| 指令 | 用户输入的一句话 | 用户说了什么？ |
| 目标表示 | `object=red_block, target=blue_goal` | 操作谁，送到哪里？ |
| 执行计划 | 接近、抓取、抬高、搬运、释放 | 准备怎样完成？ |
| 验收条件 | 已释放，且处在当前目标允许范围内 | 实际完成了吗？ |

可以把目标表示理解为交给程序的一张任务卡。任务卡写的是“蓝色区域”这个实体，蓝区的坐标则需要从观察中查询。若蓝区移动了，目标仍是同一个蓝区，原来的坐标却不再适用。

程序中的**谓词**只是一个返回真或假的判断函数。`World.success()` 就是本环境的任务成功谓词。它检查真实场景状态，而不是检查模型是否说了“完成”。具体距离、高度与速度条件会在第 9 章一起核对。

## 第一步：看一条支持的输入如何变成 JSON

在仓库根目录、已激活环境中运行：

```sh
python lab/run.py parse-goal --instruction '把红色方块放到蓝色区域'
```

完整预期输出为：

```json
{
  "status": "ready",
  "object": "red_block",
  "target": "blue_goal",
  "parser": "restricted_rules"
}
```

`ready` 表示输入通过当前规则，`restricted_rules` 表示这是一套受限规则，不是大模型。解析器做全文模板匹配：它接受“把/请把/将红色方块放到蓝色区域”等代码中明确列出的模板，忽略空白、英文大小写和末尾常见标点。

因此“将红色方块置于蓝色区域”虽然人能看懂，当前程序仍可能要求澄清。这里的澄清结果只说明**不在受支持模板内**，不代表程序理解了句子后判断它含糊。严格的边界便于我们先验证流程，再考虑更复杂的语言解析。

目前控制器和验收仍固定为红块到蓝区。解析结果的 `object/target` 展示一种目标表示，程序实际只用 `status` 决定是否允许继续；修改 JSON 的对象名称不会自动增加新任务能力。

## 第二步：拒绝含糊、不支持和否定指令

逐条运行：

```sh
python lab/run.py parse-goal --instruction '把方块放到目标区域'
python lab/run.py parse-goal --instruction '把绿色方块放到蓝色区域'
python lab/run.py parse-goal --instruction '不要把红色方块放到蓝色区域'
```

这三条输入都应返回 `needs_clarification`。输出还包含 `question`，提示当前只接受明确模板；它不会针对每种错误生成个性化问题。第三条尤其重要：“红色方块”和“蓝色区域”都出现了，但整句话是否定命令，不能仅匹配关键词就开始搬运。

`parse-goal` 只打印解析结果，不控制机器人。即使需要澄清，它也正常退出，所以检查的是 `status`，不能只看命令有没有报错。若同样的输入交给 `agent`，程序会在动作之前停止，退出码为 2，并打印澄清结果。它不会自动弹出输入框等你回答；重新提交支持的指令才会开始新回合。

## 第三步：把确认后的指令交给离线控制器

```sh
python lab/run.py agent --mode scripted --seed 7 --instruction '把红色方块放到蓝色区域' --out runs/ch07-goal
```

现在走完了“指令被接受→运行反馈循环→检查物理结果”的流程。把下面代码保存为仓库根目录的 `inspect_ch07.py`：

```python
import json
from pathlib import Path

summary = json.loads(Path("runs/ch07-goal/summary.json").read_text())
for key in ("mode", "seed", "success", "steps", "model_calls", "error"):
    print(f"{key}: {summary[key]}")
print("最终持物:", summary["final_observation"]["robot"]["holding"])
print("方块位置:", summary["final_observation"]["scene"]["block_xyz"])
print("目标位置:", summary["final_observation"]["scene"]["goal_xyz"])
assert summary["mode"] == "scripted"
assert summary["model_calls"] == 0
assert summary["success"] is True
```

```sh
python inspect_ch07.py
```

种子 7 的参考结果为 `success: True`、`steps: 7`、`model_calls: 0`、最终持物为 `False`。方块与目标的坐标不必完全相等，任务允许一定容差；也不能仅凭“很接近”自行判定成功，第 9 章会将全部验收条件打印出来。

## 第四步：在看轨迹前写下判据

先写一句话：“方块已经释放，并满足当前蓝区的放置条件。”然后再看轨迹和日志。这样可以避免看见动作顺利，就把原来的“放入蓝区”悄悄改成“机械臂移动过”。

若任务失败，按下面两个问题区分原因：

1. 输入是否正确表达并通过了预定任务？如果绿色被错误换成红色，问题在解释或校验。
2. 输入正确后，物体是否真的被搬到目标？如果抓空了或放在旧坐标，问题在执行与反馈。

本课程有限模板不会解决“整理桌面”“把它放好”这类开放指令；给它增加几条字符串匹配，也不能视为获得通用语言理解。

## 本章主线验收

保存明确模板、缺少颜色、绿色对象、否定句四种实际解析结果，以及 `runs/ch07-goal` 的执行记录。解释为什么前三个概念——输入被接受、工具返回成功、任务成功——不能互相替代。

基础练习：再写两条自己认为同义的表达，用解析命令检查。即使它们被拒绝，也如实记录“模板未支持”，不要把输出改写成语义理解成功。

进阶练习：为“先把红块放到蓝区，再把绿块放到黄区”设计任务卡。指出需要增加的物体、顺序记录与验收信息；第 16 章将实际运行双物体任务，但当前这条命令还不支持它。

离线主线到这里已经完成，可以直接进入第 8 章。目标含有“第几次”“先后顺序”时还会需要历史信息，第 10 章会接着处理。

## 选学：把决策器接到真实模型

这一节需要你已有支持 Chat Completions 函数工具调用的模型服务。**端点**是服务接收请求的网址，`AF_MODEL` 是服务识别的模型名，**API 密钥**是调用凭证。服务规格不同，不能照抄一个陌生模型名就假定兼容。

本程序从三个环境变量读取配置：`AF_BASE_URL`、`AF_MODEL`、`AF_API_KEY`。环境变量是当前终端给程序提供的配置值；不会因为在课程网页上填写文字就生效。基础地址需包含提供方要求的版本前缀，如 `/v1`，程序会追加 `/chat/completions`。

如果已经在当前终端设置好这三个变量，可直接运行：

```sh
python lab/run.py agent --mode llm --seed 7 --max-calls 12 --out runs/ch07-llm
```

还不熟悉终端环境变量时，可以用下面这个跨平台启动脚本。将它保存为包含 `lab/` 的目录中的 `run_online.py`，运行 `python run_online.py`，再按提示输入服务商给出的 API 基础地址、模型标识与自己的密钥。密钥输入不回显，也不写进文件。这个脚本与上面的命令任选一种即可；不要把服务商网页首页当成 API 基础地址。

```python
import getpass
import os
import subprocess
import sys

env = os.environ.copy()
env["AF_BASE_URL"] = input("API 基础地址（含所需版本前缀）：").strip()
env["AF_MODEL"] = input("支持工具调用的模型标识：").strip()
env["AF_API_KEY"] = getpass.getpass("API 密钥（输入不显示）：").strip()
if not all(env[key] for key in ("AF_BASE_URL", "AF_MODEL", "AF_API_KEY")):
    raise SystemExit("三项配置都需要填写；尚未发出请求。")
result = subprocess.run([
    sys.executable, "lab/run.py", "agent", "--mode", "llm",
    "--seed", "7", "--max-calls", "12", "--out", "runs/ch07-llm",
], env=env)
raise SystemExit(result.returncode)
```

`env` 是传给本次实验进程的配置字典；`sys.executable` 让它继续使用当前已经激活的 Python 环境。脚本退出后，这些输入不会自动设置到下一次新终端中。

上述两种入口都会发起真实请求，可能产生服务费用。最多尝试 12 次请求，每次输出上限 700 token、超时 60 秒；这些限制不是金额上限，输入对话会随着工具调用增长。密钥只放本机环境变量，不写入代码、课程笔记或截图。缺少配置时程序明确失败，不会自动回退为离线模式。

在线模型获得的是 `observe/move/grasp/release` 四种工具与仿真状态，没有图片。支持的任务仍受同一个目标模板限制。输出目录会增加 `model-messages.json`，用于检查实际回复与工具调用；模型返回“完成”仍要通过物理验收。

本课程已经验证离线流程和适配器的模拟测试，**没有真实模型成功率结果**。`model_calls > 0` 只证明尝试发起请求，不足以证明服务返回成功或任务完成。若自行试跑，应同时保留请求是否成功、实际回复、工具反馈与任务结果，报告使用的端点类型及模型名，不记录密钥。

## 延伸阅读

- [Python 官方 JSON 文档](https://docs.python.org/3/library/json.html)：理解结构化数据如何读取。
- [SayCan 原项目](https://say-can.github.io/)：进一步阅读语言目标与机器人技能可行性的连接；本课程未实现其方法。
- [RoboMME 计数任务案例](../gallery.html#demo-robomme-pick-count)：观察为什么“完成第几次”需要历史证据，不能只看最后一帧。
