# 第 9 章：用执行证据验证任务，并从失败中恢复

一次顺利的搬运无法证明控制器会处理意外。本章主动制造两个可重复的变化：第一次抓取失效，以及抓取后目标区域移动。用同一场景比较固定脚本与反馈控制器，看看哪些信息真正改变了动作。

前置要求：完成第 6 章日志检查与第 7 章目标验收。实验使用精确状态观察和确定性规则，不调用大模型；这里验证的是反馈机制，而非在线模型的推理能力。

## 本章目标

运行三组对照，定位第一处失败及恢复动作，用统一标准比较结果。你的结论应限定在本教学环境和所运行种子范围内，保留全部回合，而不是只展示成功视频。

## 三层“成功”不能混在一起

第一层是程序完成：命令没有崩溃。第二层是工具完成：例如某次 `move` 到达指定位置，或 `grasp` 建立附着。第三层是任务完成：红色方块已经释放，稳定处于当前蓝色目标范围内。

课程的 `World.success()` 同时检查：不再附着、水平距离小于 0.045 米、方块中心高度处于 0.015 到 0.065 米之间、平移速度小于 0.05 米每秒。每步观察中的 `scene.block_linear_speed_m_s` 记录平移速率，可与位置及持物状态一起核对。位置在日志中经过小数舍入，阈值边缘仍应以原始状态计算为准。这是当前场景的教学验收条件，不能直接作为另一种物体或真实机器人任务的标准。

其中“当前目标”很关键。若蓝区域移动后仍在旧位置放下方块，即使所有动作工具都返回正常，任务依然失败。最终验收独立于控制器的口头宣告。

## 第一步：先跑无扰动对照

```sh
python lab/run.py baseline --seed 7 --perturb none --out runs/ch09-baseline-clean
python lab/run.py agent --mode scripted --seed 7 --perturb none --out runs/ch09-agent-clean
```

固定脚本在开始时缓存方块与目标坐标，然后执行既定动作，不根据结果改计划。`scripted` 控制器每一轮读取当前状态，根据是否附着、末端与物体或目标的关系选择下一步。顺利场景下，两者都可能完成任务。

## 第二步：让第一次抓取失败

```sh
python lab/run.py baseline --seed 7 --perturb miss-grasp --out runs/ch09-baseline-miss
python lab/run.py agent --mode scripted --seed 7 --perturb miss-grasp --out runs/ch09-agent-miss
```

扰动在第一次满足抓取位置条件的 `grasp` 上触发一次，返回 `injected_miss_grasp`，不会建立附着。它是人为注入的接口失败，不代表仿真已经建模真实滑落或摩擦不足。

固定脚本继续搬运和释放，却没有物体随行。反馈控制器重新观察到没有抓住方块，可以再次尝试。这里的恢复来自显式规则，不能写成模型自行发明了重试策略。

失败回合会以非零退出码结束，属于本章预期结果；在终端逐条运行后续命令。不要用要求每条命令成功的批处理方式，让第一个预期失败阻止其他对照。

## 第三步：让目标位置发生变化

```sh
python lab/run.py baseline --seed 7 --perturb shift-goal --out runs/ch09-baseline-shift
python lab/run.py agent --mode scripted --seed 7 --perturb shift-goal --out runs/ch09-agent-shift
```

扰动在首次成功抓取后把蓝区域移到新位置。固定脚本使用缓存的旧坐标，反馈控制器根据更新后的观察移动。检查日志中 `goal_xyz` 何时变化，再检查下一次横向移动的目标，建立“观察变化导致动作变化”的证据链。

这一实验刻意缩小了问题：区域只移动一次，新位置仍在可达范围内。它不证明控制器能够追踪任意速度的动态物体，也没有验证真实碰撞、遮挡和连续视觉反馈。

## 第四步：把结果和失败事件一起读出来

运行下面的完整比较程序：

```sh
python - <<'PY'
import json
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
    failures = [event for event in events if not event["result"]["ok"]]
    print(name, "任务成功：", summary["success"],
          "工具调用：", summary["steps"], "模型调用：", summary["model_calls"])
    for event in failures:
        print("  失败步骤：", event["step"], event["tool"], event["result"].get("error"))
PY
```

预期可以观察到：无扰动时两者完成任务；两种扰动下固定脚本失败，而确定性闭环完成恢复。以实际记录为准，出现差异就保留失败并排查。尤其注意目标移动的失败可能没有任何工具报错，只有最终任务验收失败。

## 第五步：用多个回合限制结论

```sh
python lab/run.py evaluate --seeds 5 --out runs/ch09-evaluation
```

该命令对种子 0 到 4，分别运行两种控制方式与三种扰动，共 30 个回合；各回合目录与 `evaluation.json` 保留详细结果。报告每组成功数、总回合数和工具调用开销，再说明扰动定义。

不能把这 30 个简化仿真回合写成真实机械臂、通用具身任务或语言模型能力的成功率。它们支持的结论是：在这组确定性测试中，反馈与重读目标对指定失败有帮助。

## 有限恢复与排查顺序

当前规则循环最多执行 32 轮。预算是终止边界，并不保证每种失败都能恢复。重复同一条无效动作直到预算耗尽，只能说明系统没有无限运行，不能算合理恢复。

排查时先看参数是否有效，再看移动或抓取是否达成，最后看最终关系是否满足。遇到不可达坐标，应改变目标或停止；遇到暂时抓取失败，可以有限重试；遇到目标变化，应重新观察。恢复策略必须与失败原因对应。

## 本章验收、案例与练习

交付六份单回合日志、一份多回合结果，以及两个解释：抓取失败后为何重试，目标移动后为何改坐标。两条解释都必须引用具体事件，不能只引用最后的 `success`。

打开 [MemS：目标碗被推走后会怎样](../gallery.html#demo-mems-target-shift-libero-three)，把其中的观察、记忆更新和再规划与本章对照。展厅案例提供阅读材料；这里没有复现其完整感知与记忆系统。

基础题：在目标移动日志中找出第一次位置变化和随后采用新坐标的动作。进阶题：提出一个当前规则无法解决的失败，并写出识别条件、最多重试次数和终止原因；实现后再报告实验结果。

- [MemS 原始实现与空间记忆说明](https://github.com/darthjaja6/MemS)
- [PyRUA-Lean：动作结果与代码执行机制](https://dagroup-pku.github.io/PyRUA-Lean/docs/getting-started/how-it-works/)
