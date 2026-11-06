# 第 9 章：用执行证据验证任务，并从失败中恢复

第 6 章的规则循环、第 7 章的目标判据和第 8 章的误差检查，都在强调同一件事：程序说成功之前，先看实际发生了什么。本章把这个要求放进两个可重复的意外中——第一次抓空，以及抓取后目标移动。

前置要求：能读第 6 章事件日志，理解单步 `ok` 与任务 `success`。本章仍用仿真状态和离线规则，不依赖第 7 章选学的模型服务，也没有把第 8 章颜色定位接入控制器。

## 本章目标：做一组真正可以比较的实验

固定脚本与反馈控制器采用相同种子、相同扰动。这样的比较叫**对照实验**：尽量保持其他条件一致，把不同结果与决策方式联系起来。一个**回合**是从创建初始场景，到任务成功或预算结束的一次完整尝试。

我们将运行 2 种控制器 × 3 种条件，共 6 个单回合，再用 5 个种子做 30 回合检查。保留失败回合，才能知道方法何时有用。

## 先把三层“成功”分开

1. 程序运行完毕：没有在依赖或代码错误处崩溃。
2. 工具执行成功：例如一次 `move` 达到该调用要求的位置。
3. 整个任务成功：方块已释放，并满足当前蓝区的放置条件。

本环境的 `World.success()` 同时检查四项：

| 条件 | 从哪里检查 | 具体阈值 |
| --- | --- | --- |
| 已松开 | `robot.holding` | 必须为假 |
| 水平位置正确 | `scene.block_xyz` 与 `scene.goal_xyz` 的 XY 距离 | 小于 `0.045 m`，即 4.5 cm |
| 高度合理 | 方块中心 `block_xyz[2]` | 严格位于 `0.015` 与 `0.065 m` 之间 |
| 运动足够慢 | `scene.block_linear_speed_m_s` | 小于 `0.05 m/s`，即 5 cm/s |

这些数值是教学环境的约定，不是通用机器人标准。速度是在等待物体落下后采样的瞬时值，不能把一次检查扩大为“物体以后永远稳定”。位置日志保留五位小数，若恰好在阈值边缘，仍以 `World.success()` 的原始状态计算为准。

## 第一步：建立无扰动对照

在仓库根目录、已激活环境中逐条运行：

```sh
python lab/run.py baseline --seed 7 --perturb none --out runs/ch09-baseline-clean
python lab/run.py agent --mode scripted --seed 7 --perturb none --out runs/ch09-agent-clean
```

`baseline` 开始时缓存坐标，随后走固定序列；`scripted` 每轮重新看状态。无扰动时，两者的参考结果都是成功、7 次工具调用。这个结果说明两者都能完成顺利场景，尚不能说明谁更会处理故障。

每条命令都会新建世界，不会接着上一条命令的末态运行。相同种子用于匹配初态，独立输出目录用于避免覆盖证据。

## 第二步：只让第一次有效抓取失败

```sh
python lab/run.py baseline --seed 7 --perturb miss-grasp --out runs/ch09-baseline-miss
python lab/run.py agent --mode scripted --seed 7 --perturb miss-grasp --out runs/ch09-agent-miss
```

`miss-grasp` 是**故障注入**：人为在指定时刻制造已知错误，以便比较系统反应。它在第一次满足位置条件的 `grasp` 上返回 `injected_miss_grasp`，不建立附着；之后的有效抓取可正常发生。它不模拟真实滑落或摩擦不足。

抓空后，固定脚本仍搬运并释放空夹爪，最终失败。反馈控制器在下一轮看到 `holding: false`，且工具仍在方块附近，于是再次尝试抓取。恢复规则是人工编写的，不是模型临场发明的。

基线失败时退出码为 **2**，但仍会写出日志；这是预期结果。不要用 `&&` 把两条命令连起来，因为第一条非零退出会阻止第二条执行。在普通终端逐条运行即可。反馈控制器的参考结果是成功、8 次工具调用，多出来的一次就是重试抓取。

## 第三步：让蓝色目标移到另一侧

先看同一教学环境的固定序列录像。观看时记住两个位置：抓取之前蓝区在哪里，抓取之后蓝区在哪里；然后看机械臂究竟把方块送向哪一个位置。

<!-- course-demo: course-shift-baseline -->

固定序列已经保存了旧目标位置，因此即使蓝区移走，仍会在旧位置放下。这里可以出现“各个工具都执行正常，但任务失败”：释放确实发生了，只是地点不对。

再看反馈控制器。两段录像都使用种子 7 与 `shift-goal` 条件，区别是是否根据当前观察重新选择动作。观看时寻找第一次体现新目标坐标的横向移动。

<!-- course-demo: course-shift-feedback -->

反馈控制器先抬高，再向移动后的蓝区运输。图像帮助理解动作差异，下面的日志用于确认目标何时改变、动作采用了什么坐标；视频本身不替代验收。

在自己的环境运行同一对照：

```sh
python lab/run.py baseline --seed 7 --perturb shift-goal --out runs/ch09-baseline-shift
python lab/run.py agent --mode scripted --seed 7 --perturb shift-goal --out runs/ch09-agent-shift
```

扰动在第一次成功抓取后，把蓝区从 `(0.08,-0.18)` 移到 `(0.08,0.20)` 米。新位置仍然可达，且只移动一次。这里不检验任意动态追踪、视觉感知或碰撞避障。

## 第四步：一次读出全部六组结果

把以下代码保存为仓库根目录的 `inspect_ch09.py`：

```python
import json
import math
from pathlib import Path

names = (
    "baseline-clean", "agent-clean", "baseline-miss",
    "agent-miss", "baseline-shift", "agent-shift",
)
for name in names:
    folder = Path("runs") / f"ch09-{name}"
    summary = json.loads((folder / "summary.json").read_text())
    events = [json.loads(line) for line in
              (folder / "events.jsonl").read_text().splitlines()]
    observation = summary["final_observation"]
    scene = observation["scene"]
    checks = {
        "released": not observation["robot"]["holding"],
        "near_current_goal": math.dist(scene["block_xyz"][:2],
                                       scene["goal_xyz"][:2]) < 0.045,
        "height_ok": 0.015 < scene["block_xyz"][2] < 0.065,
        "slow_enough": scene["block_linear_speed_m_s"] < 0.05,
    }
    print(name, "success=", summary["success"], "steps=", summary["steps"])
    print("  从最终日志复核:", checks)
    for event in events:
        if not event["result"]["ok"]:
            print("  工具失败:", event["step"], event["tool"],
                  event["result"].get("error"))
    assert summary["model_calls"] == 0

print("\n移动目标的事件证据：")
for name in ("baseline-shift", "agent-shift"):
    path = Path("runs") / f"ch09-{name}" / "events.jsonl"
    events = [json.loads(line) for line in path.read_text().splitlines()]
    grasp_index = next(i for i, event in enumerate(events)
                       if event["tool"] == "grasp")
    before = events[grasp_index - 1]["result"]["observation"]
    after = events[grasp_index]["result"]["observation"]
    print(name, "抓取前目标:", before["scene"]["goal_xyz"],
          "抓取后目标:", after["scene"]["goal_xyz"])
    for event in events[grasp_index + 1:]:
        if event["tool"] == "move":
            print("  后续move:", event["step"], event["arguments"])
```

```sh
python inspect_ch09.py
```

第一部分分别检查释放、水平位置、高度与速度。`math.dist` 计算两点距离，`[:2]` 只取 XY；与第 8 章不同，这里比较的是两个状态位置，不是视觉预测误差。参考结果为：

| 条件 | 固定脚本 | 反馈控制器 |
| --- | --- | --- |
| 无扰动 | 成功，7 次调用 | 成功，7 次调用 |
| 首次抓空 | 失败，7 次调用 | 成功，8 次调用 |
| 目标移动 | 失败，7 次调用 | 成功，7 次调用 |

第二部分应显示两组目标都从旧位置变到新位置；后续 `move` 参数却不同。先抬高的动作仍使用工具当前位置，不能把它误当成“控制器忽略了新目标”。继续看后面的运输动作：固定序列仍采用 `y=-0.18`，反馈策略采用 `y=0.20`。

抓空基线会出现工具错误；目标移动基线却可能没有任何工具报错。正因为如此，需要独立的任务检查，不能只统计工具 `ok` 的比例。

## 第五步：用多个种子检查结论

```sh
python lab/run.py evaluate --seeds 5 --out runs/ch09-evaluation
```

此处 `--seeds 5` 表示使用种子 **0 到 4**，不是“使用种子 5”。两种控制器 × 三种条件 × 五个种子，共 30 回合。终端按组显示成功数，每回合目录及 `evaluation.json` 保留明细。参考结果为无扰动两策略均 5/5；两种扰动下基线均 0/5，反馈策略均 5/5。

实验能够支持“这组规则在这些条件下对两种故障有效”。它没有测试更多物体、任意扰动、真实机械臂或在线模型，不应写成通用可靠性结论。不同结果也要保留，先核对版本、种子、条件与失败事件。

## 恢复必须有限，也必须针对原因

当前规则最多执行 32 轮。预算指允许继续尝试的次数；耗尽后结束，避免无限循环。但“有次数上限”不等于“恢复方法正确”。

例如暂时抓空可以尝试重抓；目标已移动需要重读位置；不可达位置重复调用 32 次也不会因此变得可达。今后扩展控制器，应同时写清错误如何识别、采取什么不同动作、最多重试几次、何时停止。

本章验收包括六组单回合日志、30 回合结果，以及两条具体证据链：“抓空→未持物→再次抓取”和“目标改变→运输坐标改变→当前目标验收通过”。

基础练习：指出目标移动基线中哪个任务条件为假，而哪些工具仍然成功。进阶练习：为“连续三次抓取都失败”写一条停止规则，先说明期望日志，再实现测试；不要把现有只失败一次的实验当成已经验证该规则。

下一章保留这些事件证据，解决另一个问题：这次任务已经完成，如果同一请求再次出现，程序怎样知道自己做过，又怎样确认结果现在仍然有效？

## 参考

- [本课程控制器与成功判据](https://github.com/Glaz-j/agent-fieldnotes/blob/main/lab/run.py)
- [MemS 目标移动展厅案例](../gallery.html#demo-mems-target-shift-libero-three)：阅读更复杂的感知与记忆系统时，沿用本章的证据检查方法；本实验不等于复现该系统。
