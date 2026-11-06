# 第 6 章：搭起第一个机器人 Agent 循环

第 5 章已经能用固定顺序完成一次抓放：移动、抓取、搬运、释放。现在只改一个地方：不再预先决定全部动作，而是在每一步结束后重新看状态，再选下一步。这就是本章要搭起的反馈循环。

前置要求：完成第 2 章安装，能运行第 5 章的 `baseline`，知道 `move`、`grasp`、`release` 各做什么。本章全部离线运行，不需要注册模型服务或填写密钥。后面的命令都在含有 `lab/` 的仓库根目录、已激活的虚拟环境中执行。

## 本章目标：看懂一次决策为什么发生

完成红色方块到蓝色区域的搬运，得到 `events.jsonl` 和 `summary.json`。完成后，你应能指着日志解释：“这一步为什么抓取？抓取后为什么抬高？什么时候该停止？”

这里的 Agent 循环是“观察—决策—行动—再观察”的软件结构。当前决策器是一组人工写好的规则，名称为 `scripted`；确定性意味着相同状态会得到相同选择。它不是大模型推理。以后可以替换决策器，但观察、工具和任务验收这些接口仍然需要保留。

## 先用一个具体意外理解闭环

假设第三步抓空了。固定脚本仍然执行第四步“抬高”、第五步“移到蓝区”，只是这次没有方块跟随。反馈控制器会先重新读取 `holding`：它表示方块是否已经附着在工具上。若还是 `false`，就不会进入“搬运已抓物体”的分支。

**闭环**指执行结果会影响后续动作；这里闭合的是信息回路，不是机械臂走了一条闭合曲线。**状态机**则是编写这种规则的一种方式：根据“尚未抓住”“已经抓住”“任务完成”等状态选择动作。

下面是结构说明，不是需要复制执行的 Python：

```text
最多进行 32 轮：
    读取当前观察
    如果任务已经完成：结束
    根据是否持物、工具位置和目标位置选择一个动作
    执行动作，并记录动作返回的观察
仍未完成：保留失败结果并结束
```

实际 `scripted_agent` 在下一轮调用 `observe()` 读取当前状态，不靠理解错误消息文字来恢复。例如抓空后，它看到 `holding` 仍为假，于是继续满足抓取分支。`error` 字段主要留给我们排查原因。

## 第一步：认清工具、观察与任务三个接口

| 接口或字段 | 本章中的作用 | 一个容易混淆的地方 |
| --- | --- | --- |
| `observe()` | 读取机器人、方块、目标的当前状态 | 本章坐标直接来自仿真器，不是相机识别 |
| `move(x,y,z)` | 让工具尝试到达世界坐标，单位米 | 到达方块旁边不等于抓住方块 |
| `grasp()` | 在足够靠近时建立教学抓取附着 | `holding` 才能帮助确认是否已持物 |
| `release()` | 解除附着并等待物体落下 | 在错误位置放下也可能 `ok: true` |
| `task.success` | 判断整个搬运任务是否完成 | 它与单个工具的 `result.ok` 不同 |

`World` 还提供颜色定位接口，留到第 8 章单独练习。本章不使用图像。抓取采用简化 SCARA 与显式附着约束，目的是学习控制流程，不代表验证了真实夹爪摩擦。

## 第二步：运行一次无扰动的闭环

```sh
python lab/run.py agent --mode scripted --seed 7 --out runs/ch06-scripted --perturb none
```

参数从左到右表示：运行 Agent、使用规则模式、采用种子 7、把文件写入指定目录、不注入扰动。种子控制初始方块的位置；固定种子有助于比较两个方法。命令默认只计算物理过程、打印结果，不会弹出动画窗口，这是正常现象。

本机参考结果的关键字段如下，其余完整状态仍保存在文件里：

```json
{
  "mode": "scripted",
  "seed": 7,
  "perturb": "none",
  "success": true,
  "steps": 7,
  "model_calls": 0,
  "error": null
}
```

这里 `null` 表示没有记录到程序异常，不是所有问题都不存在：一次任务也可能 `error: null` 但 `success: false`。`steps` 是保存的工具事件数，`model_calls` 是尝试的模型请求次数。`model_calls: 0` 说明这次没有调用模型。

## 第三步：把七次动作与规则逐项对应

下表描述种子 7、无扰动时的七次工具调用。`p` 代表当前方块位置，`g` 代表当前目标位置；高度 `0.18 m` 用于抬升，`0.06/0.065 m` 用于接近与放置。

| 事件 `step` | 工具 | 决策依据 | 调用后的关键变化 |
| --- | --- | --- | --- |
| 0 | `move(p.x,p.y,0.18)` | 空手，工具的水平位置还不靠近方块 | 到方块上方 |
| 1 | `move(p.x,p.y,0.06)` | 水平位置已接近，但工具太高 | 下降到抓取附近 |
| 2 | `grasp()` | 空手且已接近方块 | `holding` 变为 `true` |
| 3 | `move(tool.x,tool.y,0.18)` | 已持物，要横向移动但目前过低 | 先抬高 |
| 4 | `move(g.x,g.y,0.18)` | 已持物且高度合适，还没到目标上方 | 移向当前蓝区 |
| 5 | `move(g.x,g.y,0.065)` | 已到目标上方，但仍然较高 | 降低准备放置 |
| 6 | `release()` | 已持物且达到放置位置 | 松开，等待物体落下 |

下一轮读取到 `task.success: true`，循环结束。这张表解释本次轨迹，不是程序硬编码的七行执行计划；第 9 章注入抓空后，规则会多执行一次抓取。

## 第四步：用小程序读日志

JSON 是保存一份结构化数据的格式；JSONL 则是“一行一个 JSON 对象”，适合保存连续事件。`summary.json` 是本回合汇总，`events.jsonl` 是逐步记录。`step` 从 0 开始，所以 `step: 2` 是第三次事件。

把以下完整代码保存为仓库根目录的 `inspect_ch06.py`，再执行它。保存为文件的方式适用于 macOS、Linux 和 Windows，无需学习不同终端的多行输入语法。

```python
import json
from pathlib import Path

folder = Path("runs/ch06-scripted")
summary = json.loads((folder / "summary.json").read_text())
events = [json.loads(line) for line in
          (folder / "events.jsonl").read_text().splitlines()]

print("任务成功:", summary["success"], "模型调用:", summary["model_calls"])
print("step  tool     ok     holding  task_success")
for event in events:
    result = event["result"]
    observation = result["observation"]
    print(event["step"], event["tool"], result["ok"],
          observation["robot"]["holding"], observation["task"]["success"])

assert summary["mode"] == "scripted"
assert summary["model_calls"] == 0
assert len(events) == summary["steps"]
assert summary["success"] is True
```

```sh
python inspect_ch06.py
```

应看到七行事件，第三行抓取之后 `holding` 为 `True`，最后释放后为 `False` 且任务成功。Python 打印的 `True/False` 与 JSON 中的 `true/false` 含义相同。`assert` 是检查条件的语句；条件不成立时会抛出错误，提醒你检查证据，而不是继续宣称通过。

每行观察是**该动作执行之后**的状态。要了解抓取前发生了什么，应看前一条移动事件的观察，不能把抓取后的 `holding: true` 当成抓取前已有物体。下一步为什么抬高，则需要结合抓取后的观察与上面的决策表。

## 验收与常见卡点

本章验收需要两个日志文件和一个解释：抓取前工具在哪，抓取后哪个字段变化，为什么随后选择抬高。仅有最终 `success` 不能展示你读懂了闭环。

- 找不到日志：确认从仓库根目录运行，并检查 `--out` 指定的目录；命令不会自动沿用上一章的输出位置。
- 没有动画：本命令不打开交互查看器，先用事件表检查动作，后续课程提供实际录像对照。
- 看见 `ok: true` 就认为完成：继续检查 `task.success`，尤其注意释放发生的位置。
- 七次动作与固定基线完全一样：无扰动时本来就可能相同，要通过第 9 章对照检验反馈的作用。

基础练习：换成 `--seed 8 --out runs/ch06-seed8`，并修改检查程序的目录。比较初始位置与动作类型，解释为什么坐标变了，任务阶段仍可相同。

下一章先解决“什么任务可以被接受、怎样才算完成”。真实模型接入放在第 7 章末作为选学；跳过它不影响后续任何离线实验。以后阅读 [PyRUA-Lean 的代码组织案例](../gallery.html#demo-pyrualean-astra-cells-20261028)时，可以继续追问“反馈在哪一行改变了下一步”，但它的机器人与接口不同，不是本章已经复现的系统。

## 参考

- [课程循环与工具实现](https://github.com/Glaz-j/agent-fieldnotes/blob/main/lab/run.py)
- [MuJoCo 3.3.7 Python 接口](https://mujoco.readthedocs.io/en/3.3.7/python.html)
