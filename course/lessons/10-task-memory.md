# 第 10 章：任务记忆——记住做过什么，也保留依据

第 9 章让机器人在当前回合内发现抓空、重试，并在目标移动后改变动作。现在把那次成功保留下来：如果收到第二次相同请求，系统怎样知道自己做过？它又怎样确认结果现在仍然有效？

前置要求：能读第 6、9 章的技能事件与任务验收。继续使用同一个虚拟环境，新增入口是 `lab/advanced.py`，不需要安装新依赖或配置模型。本章的记忆是普通 Python 数据结构与日志，不是修改模型参数。

## 本章目标：为“已经完成”保存可检查的依据

先运行两次相同任务请求，检查第二次为什么没有新增搬运动作。再做一个小实验：完成后移动目标，验证旧的“已完成”标记会被复核并失效，而不是永远有效。

## 四种记录，回答四个不同问题

| 记录 | 回答的问题 | 本课程里的例子 |
| --- | --- | --- |
| 任务请求 | 现在要求处理哪项任务？ | `red_to_blue` |
| 技能事件 | 实际调用过什么、返回什么？ | `step=2` 的抓取事件 |
| 当前观察 | 方块和目标现在在哪里？ | `World.observe()` 的状态 |
| 完成凭据 | 哪项任务何时通过了验收？ | `TaskMemory.completed` 保存的观察 |

**凭据**就是支持一个结论的记录。例如“调用过 `release`”只能证明尝试了释放；“在仿真时刻 9.4 秒，方块已释放且通过放置检查”，才是完成依据。当前物体仍在不在目标区，还要重新检查。

**任务 ID** 是稳定标识，用于把重复提交关联到同一任务。本实验直接用字符串 `red_to_blue`，只在同一个仿真世界中使用。真实系统还需要区分场景、对象和任务版本，不能把另一个场景中同名任务的完成状态拿来复用。

重复处理同一请求时避免重复效果，常称为**幂等处理**。这里可以用一个更直观的说法理解：用户再次要求“把红块放到蓝区”，若这件事现在已经成立，就不必再拿起来放一遍。但检查可以重复，搬运动作不一定要重复。

## 第一步：画出写入记忆的时机

本章的 `TaskMemory` 只做三件事：核对已有完成记录、在任务成功时保存证据、在原条件不再成立时删除当前完成标记。实际执行仍由上一章的规则控制器负责。

```text
收到任务 ID
    |
    v
是否已有这个 ID 的完成凭据？
    | 否                         | 是
    v                            v
执行规则控制器              重新检查当前任务条件
    |                            |
    v                            +-- 仍满足：跳过重复搬运
检查 World.success()             |
    |                            +-- 不满足：移除完成标记，再执行
    +-- 真：记录当前观察与时间
    +-- 假：不登记为完成
```

注意两次检查的位置：第一次防止把失败写成完成，第二次防止把过去成功当作现在仍然成功。`TaskMemory` 本身不会阅读自然语言或决定抓取参数。

## 第二步：运行两次相同请求

在仓库根目录、激活课程环境后执行：

```sh
python lab/advanced.py memory --seed 7 --out runs/ch10-memory
```

程序在同一个世界里依次处理两个 `red_to_blue`。参考输出的关键字段为：

```json
{
  "requests": ["red_to_blue", "red_to_blue"],
  "completed_ids": ["red_to_blue"],
  "skipped_duplicates": 1,
  "action_calls": 7,
  "success": true
}
```

两次请求只产生第一轮的七次技能调用；第二次重新检查成功条件后跳过。`skipped_duplicates: 1` 不是“没有检查第二次”，而是“检查之后没有重复执行动作”。

每次重新运行命令都会创建新世界与新记忆。文件用于保存本次证据，程序不会自动读取上次 `memory.json` 来恢复跨进程记忆。这一区别很实际：关闭程序后再运行，不等于同一个机器人一直记着上次任务。

这个实验也没有证明“去掉记忆就一定重复搬运”。原来的反馈控制器本来就先检查 `success`，可能同样不再行动。本章关注的是任务身份、完成证据与复核过程；要评价记忆是否提高效率，还需要另设公平对照。

## 第三步：把任务事件与技能事件连起来

输出目录中的三个文件各有用途：

- `summary.json` 汇总请求、完成项与调用数。
- `events.jsonl` 逐行记录机器人实际执行的技能。
- `memory.json` 保存完成凭据及记忆管理事件。

`memory.json` 中 `completed.red_to_blue` 包含 `source/at_sim_time_s/observation`。其中 `source` 为 `simulator_state`，时间是仿真时间，不是电脑时钟。`events` 包含首次 `completed` 与随后 `revalidate_completion`，后者用 `valid_now` 表示当前复核结果。

把以下完整代码保存为仓库根目录的 `inspect_ch10.py`：

```python
import json
import math
from pathlib import Path

folder = Path("runs/ch10-memory")
summary = json.loads((folder / "summary.json").read_text())
memory = json.loads((folder / "memory.json").read_text())
actions = [json.loads(line) for line in
           (folder / "events.jsonl").read_text().splitlines()]
evidence = memory["completed"]["red_to_blue"]

print("请求:", summary["requests"])
print("跳过重复搬运:", summary["skipped_duplicates"])
print("动作总数:", len(actions))
print("凭据来源:", evidence["source"])
print("完成时刻:", round(evidence["at_sim_time_s"], 3), "仿真秒")
print("最后动作:", actions[-1]["tool"], actions[-1]["sim_time_s"])
for event in memory["events"]:
    print("记忆事件:", event["event"],
          "当前有效:", event.get("valid_now", "完成事件另有observation凭据"))

assert evidence["observation"]["task"]["success"] is True
assert actions[-1]["tool"] == "release"
assert math.isclose(evidence["at_sim_time_s"], actions[-1]["sim_time_s"], abs_tol=0.001)
assert summary["action_calls"] == len(actions) == 7
assert memory["events"][-1]["valid_now"] is True
```

```sh
python inspect_ch10.py
```

应看到七次动作、完成时间约 9.4 仿真秒、最后动作是 `release`，然后是完成记录与有效的重复请求复核。时间可能显示很多小数，是浮点计算的正常现象，所以这里用 `math.isclose` 比较，并允许 0.001 秒差异。

这里没有把“原计划写过 release”当成证据：`events.jsonl` 保存的是已经执行的调用及返回观察，完成记录又要求该状态通过验收。完整证据链是“实际释放→成功状态→保存凭据→重新检查后跳过”。

## 第四步：亲自让旧凭据失效

现在保留“过去成功过”的历史，同时让“现在仍然成功”为假。把下面代码保存为仓库根目录的 `invalidate_ch10.py`：

```python
import mujoco
from lab.run import World, scripted_agent
from lab.advanced import TaskMemory

world = World(seed=7)
memory = TaskMemory()
task_id = "red_to_blue"

scripted_agent(world)
assert memory.remember(task_id, world)
print("第一次完成:", world.success())
print("立即重复请求可跳过:", memory.skip_completed(task_id, world))

# 实验用故障注入：直接移动目标，更新仿真中的位置计算。
# 这两行不是机器人技能，也不是由相机检测出目标移动。
world.data.mocap_pos[0, :2] = [0.08, 0.20]
mujoco.mj_forward(world.model, world.data)

print("移动目标后当前成功:", world.success())
print("再次请求可跳过:", memory.skip_completed(task_id, world))
print("当前完成表仍有该ID:", task_id in memory.completed)
print("历史中仍有完成事件:",
      any(event["event"] == "completed" for event in memory.events))

scripted_agent(world)
assert memory.remember(task_id, world)
print("重新搬运后完成:", world.success())
```

```sh
python invalidate_ch10.py
```

参考输出依次是：

```text
第一次完成: True
立即重复请求可跳过: True
移动目标后当前成功: False
再次请求可跳过: False
当前完成表仍有该ID: False
历史中仍有完成事件: True
重新搬运后完成: True
```

`mocap_pos` 是本场景中目标的可移动位置数组；`mj_forward` 更新依赖这些位置的仿真计算。现在只需要理解它们用于人为改变目标，不必掌握 MuJoCo 全部内部接口。

当前完成表删除了过期标记，历史事件却仍保存第一次成功；恢复之后会产生新的完成凭据。这两种记录分别回答“当前还有哪些任务算完成”和“以前发生过什么”，不应互相覆盖。第 11 章会进一步给目标位置本身增加来源与时效。

## 看一个更完整的记忆案例

观看下面的 Panda 抓取案例前，先提出两个观察问题：机械臂接近红块时有没有调整位置？夹爪闭合后，方块是否真的离开桌面并持续保持？这些现象可以从录像中观察；系统如何保存历史，还要结合案例来源与运行说明。

<!-- course-demo: roboicl-panda-memory-lift-20261029 -->

这段展厅素材采用 RoboICL 官方记忆组件的本地 Panda 适配，记录当前与历史图像、实际动作和回执。它展示的是接近、夹持与抬升，本章则是简化 SCARA 的放置任务，两者机器人、工具与任务都不同。

视频中看到持续夹持，并不能单独证明“有记忆优于无记忆”；那需要匹配条件的对照。它更适合帮助我们理解：如果只保存模型计划，却删掉实际动作回执，就无法分清哪些动作执行过、哪些被拒绝，以及持物状态何时改变。完整范围与来源见 [案例详情](../gallery.html#demo-roboicl-panda-memory-lift-20261029)。

## 验收、排错与下一步

本章交付 `runs/ch10-memory`、记录检查输出和失效实验输出。你应能分别指出旧成功证据、当前失败状态、失效复核和重新完成的记录，而不把它们压成一句“系统记得了”。

- 任务明明一样却没有复用：先检查 ID、场景是否一致，以及本次是否重新启动了一个世界。
- 目标已经移动却仍跳过：确认是否调用了当前状态复核，而不是只查 ID 是否存在。
- 凭据与技能数量不一致：先核对输出目录，避免把两次回合的文件混在一起。
- 失败尝试被标记为完成：检查写入是否确实经过 `World.success()`，不能只看控制循环结束。

基础练习：用 `--seed 8 --out runs/ch10-memory-seed8` 重跑，并修改检查程序目录。进阶练习：在失效实验中，比较 `memory.completed` 与 `memory.events` 的变化，解释为什么删除当前标记不应删除过去事实。

到这里，我们已经能回答“以前完成过吗”和“现在还成立吗”。下一章把同样的检查思路用于空间位置：一条曾经正确的坐标，过了多久、发生什么变化后应当重新观察？

## 参考

- [课程任务记忆实现](https://github.com/Glaz-j/agent-fieldnotes/blob/main/lab/advanced.py)
- [RoboICL 原始代码与记忆组件](https://github.com/Mosi-AI/RoboICL)
