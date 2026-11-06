# 第 10–16 章进阶实验

本模块在第一期真实 MuJoCo 环境上增加可检查的任务记忆、空间缓存、主动观察、JSON 技能程序、轻量监督学习和双物体任务。沿用 `lab/requirements.txt` 与虚拟环境，不增加依赖。所有实验都是离线程序，`model_calls` 始终为 0。

## 快速运行

在仓库根目录、已安装并激活的环境下运行：

```bash
python lab/advanced.py memory --seed 7 --out runs/memory
python lab/advanced.py spatial --seed 7 --out runs/spatial
python lab/advanced.py active-view --seed 7 --out runs/active-view
python lab/advanced.py program --seed 7 --program lab/example-program.json --budget 64 --out runs/program
python lab/advanced.py learned-skill --seed 7 --out runs/learned-skill
python lab/advanced.py benchmark --seeds 5 --out runs/benchmark
python lab/advanced.py capstone --seed 7 --perturb miss-grasp --out runs/capstone
python -m unittest discover -s lab -p 'test_*.py' -v
```

安装方法与第一期模型边界见 [GUIDE.md](GUIDE.md)。这些实验保留简化 SCARA、焊接约束近似抓取和状态观测方式。它们不是在线语言模型、VLA、真实夹持或真实机器人安全验证。`active-view` 需要可用的渲染环境，其余默认命令只运行物理计算。

每个实验写出 `summary.json` 和 `events.jsonl`，其他文件见下文。每次命令创建新的场景；不同实验使用不同 `--out`，避免覆盖旧结果。明确的程序错误或任务失败退出码为 2；包含预期失败对照的 `spatial/benchmark/learned-skill` 成功完成统计时退出 0，应读取各组指标。

## 10：带证据的任务历史

`memory` 连续接收两次 `red_to_blue` 请求。第一次通过真实动作完成任务后，`TaskMemory.remember` 才记录 `source/at_sim_time_s/observation`；第二次先检查当前物理状态是否仍满足任务，再决定跳过。

`summary.json` 包含 `requests/completed_ids/skipped_duplicates/action_calls/success`。`memory.json` 包含 `completed` 字典和 `events` 列表，事件包括 `completed` 与 `revalidate_completion`。当物体或目标变化导致原完成状态失效时，`skip_completed` 删除该完成记录，允许重新执行。

这个实验展示显式任务身份、历史证据和当前复核。它没有证明“没有记忆就一定重复动作”：当前状态控制器本身也先检查成功谓词。历史记录解决的是可追溯性和跨请求的任务管理，不能替代当前观察。

## 11：空间信息的来源和时效

`spatial` 在相同种子下运行 `stale` 和 `refresh` 两个真实场景。两者都在首次抓取后把蓝色目标从 `(0.08,-0.18)` 移到 `(0.08,0.20)`。抓取前缓存的目标位置超过两秒有效期；陈旧对照故意忽略失效信号，刷新策略重新读取当前观测。

`SpatialMemory` 的记录包括：

| 字段 | 含义 |
| --- | --- |
| `entity/xyz` | 实体身份与米制位置 |
| `source` | 本实验为 `simulator_state` |
| `observed_at_s` | 取得观测时的仿真时间 |
| `valid` | 当前记录是否可用 |
| `invalidated_at_s/reason` | 失效时间及 `expired/position_changed/superseded` 原因 |
| `update_reason` | 新记录由普通观测还是位置变化产生 |

`lookup(now, max_age_s=2.0)` 不会悄悄返回过期坐标。有效记录被新观测替换时会失效；即使旧记录已因过期失效，新记录仍会标记是否发现 `position_changed`。`spatial-memory.json` 分别保留两组缓存历史，`summary.cases` 包含 `mode/success/cache_expired/used_goal_xyz/final_observation`。

这里直接读取仿真状态演示缓存更新。缓存时间戳不是相机时间同步、空间建图或真实世界持久记忆系统。

## 12：为观察而行动

`active-view` 的相机始终固定。先实际渲染 RGB 并做颜色定位，然后把机械臂工具移动到 `(0.05,-0.23,0.24)`，再渲染与定位。这个固定动作让机械臂离开种子 7 红块的遮挡区域，没有通过隐藏真值搜索最佳视点。

输出 `before.png/after.png`；`summary.before/after` 分别含 `pixels/estimate_xyz/xy_error_m/detection/truth_xyz_for_evaluation_only`。定位来自 RGB 颜色阈值与已知相机、已知表面高度；物体真值只用于计算评价误差，不参与定位函数。命令不做视觉抓放闭环，也没有自适应视点规划器。

种子 7 的实测：75 个红色像素增加到 306 个，XY 误差由 `0.01607468 m` 降至 `0.00169828 m`。其他种子可能原本就没有遮挡，因此不能预先保证每次移动都改善指标。图像和误差必须一起看。

## 13：受限 JSON 技能程序

`example-program.json` 是完整可运行实例。程序由解释器读取数据并调用白名单技能，不执行 Python、shell、`eval` 或 `exec`。

```json
{
  "version": 1,
  "steps": [
    {"call": "move", "args": {"x": "block.x", "y": "block.y", "z": 0.18}},
    {"call": "move", "args": {"x": "block.x", "y": "block.y", "z": 0.06}},
    {"repeat": 3, "steps": [
      {"if": "not_holding", "then": [{"call": "grasp"}]}
    ]}
  ]
}
```

上例只负责接近并尝试抓取，不会完成搬运；完整实例另有抬升、移动到当前目标、下降、释放与观察。

允许的工具只有 `observe/move/grasp/release`。条件只有 `holding/not_holding/success/not_success/last_ok`，`else` 可以省略。`repeat` 只能是 1–16 的整数。坐标值可以是有限数字，或 `block.x/block.y/goal.x/goal.y/tool.x/tool.y`；这些引用在执行该调用时读取最新状态，不是字符串求值。`move` 仍受第一期工作空间与低位横移限制。

文件最大 64 KiB，最多 128 个语法节点，嵌套深度最多 6。整个文档先通过检查，任何分支里有未知工具或错误结构都会拒绝，不会先执行前面的合法动作。`--budget` 默认 64、范围 1–512，每个执行节点都扣预算，包括条件和重复节点。耗尽后返回 `program_budget_exhausted`，不继续执行后续动作；程序不是事务，已经完成的物理动作不会回滚。

```bash
python lab/advanced.py program --perturb miss-grasp --budget 64 --out runs/program-ok
python lab/advanced.py program --perturb miss-grasp --budget 2 --out runs/program-budget
```

第二条预期退出 2。摘要含 `executed_nodes/budget/error/success/tool_calls/final_observation`，输出目录保留实际使用的 `program.json`。默认 `--perturb` 为 `miss-grasp`，也可选 `none/shift-goal`。这是受限程序解释器演示，不是通用恶意代码沙箱，也不证明物理执行安全。

## 14：真正拟合一个局部技能

`learned-skill` 用解析逆运动学专家生成 80 组 XY→两关节角度样本，再用 NumPy 最小二乘实际求出参数。输入先用训练集均值与标准差归一化，特征为 `[1,x,y,x²,xy,y²]`，输出为两关节角度。它是一个局部监督学习的到达技能，不学习抓取，不读取图像或语言，不是 VLA。

训练与分布内测试区域是 `x∈[-0.14,-0.02], y∈[0.02,0.14]` 米；分布外测试区域是 `x∈[0,0.15], y∈[-0.24,-0.12]` 米。两区各有 20 个测试目标，高度均为 0.18 米，测试点不参与拟合。求解器行为见 [NumPy 2.2 的 lstsq 文档](https://numpy.org/doc/2.2/reference/generated/numpy.linalg.lstsq.html)。

预测的角度会实际写入 MuJoCo 位置伺服控制器，并推进 700 步仿真；超出关节控制范围时裁剪到 `[-3.14,3.14]`，逐条记录 `clipped`。它没有调用解析 IK 来偷偷替换预测。解析专家作为独立对照在完全相同的测试点运行。达标条件是实际工具三维位置误差小于 2 cm。

文件包括 `dataset.json`（训练标签与测试点）、`weights.json`（归一化参数与拟合权重）、`reach-results.json`（逐样本执行结果）。`summary.groups` 按 `split/policy` 汇总 `samples/successes/mean_position_error_m`。此实验直接执行伺服控制，逐样本记录在 `reach-results.json`，`events.jsonl` 为空。

种子 7 实测：

| 测试区域 | 学习策略达标 | 学习平均误差 | 解析对照达标 |
| --- | --- | --- | --- |
| ID | 20/20 | 0.001154 m | 20/20 |
| OOD | 6/20 | 0.041100 m | 20/20 |

这是一个有意局限在小区域拟合的模型。该对照展示外推误差，不能推断更复杂学习系统都具有相同表现。

## 15：匹配种子和单项消融

`benchmark --seeds 5` 使用种子 0–4，每个种子运行 `none/miss-grasp/shift-goal` 三种条件，每种条件运行四个策略，共 60 个真实 MuJoCo 回合。

- `baseline`：第一期固定序列。
- `feedback`：每步根据当前状态决策，允许失败后重试。
- `no-retry`：与 feedback 使用同一控制器，但任何技能失败后立即停止。
- `stale-spatial`：与 feedback 使用同一控制器，但始终使用初始目标坐标。

后三者共享 `feedback_controller`，通过两个开关关闭重试或目标刷新。每回合最多 32 个技能调用。`episodes.json` 保存 `seed/perturb/policy/success/tool_calls/initial_observation/final_observation`，能够直接核对同一 seed、同一扰动下四个初态相同。`summary.groups` 给出成功数与平均调用数。

本机 5 种子对照：

| 条件 | baseline | feedback | no-retry | stale-spatial |
| --- | --- | --- | --- | --- |
| none | 5/5 | 5/5 | 5/5 | 5/5 |
| miss-grasp | 0/5 | 5/5 | 0/5 | 5/5 |
| shift-goal | 0/5 | 5/5 | 5/5 | 0/5 |

移动目标下陈旧策略运行满 32 次，成功数仍为零。一次失败后停止的策略调用数更少，但完成率也低；因此不能只用平均调用数判断哪个策略好。这些是控制条件下的小样本教学实验，不是部署可靠性估计。

## 16：双物体毕业任务

`capstone.xml` 在同一个场景中加入第二个真实自由刚体与第二个目标。红色方块送到蓝色区域，绿色方块送到黄色区域。两个物体拥有独立的焊接抓取约束；同一台机械臂依次完成请求 `red, green, red`，第三个请求通过完成记录与当前状态复核后跳过。

```bash
python lab/advanced.py capstone --seed 7 --perturb none --out runs/capstone-none
python lab/advanced.py capstone --seed 7 --perturb miss-grasp --out runs/capstone-miss
python lab/advanced.py capstone --seed 7 --perturb shift-goal --out runs/capstone-shift
python lab/advanced.py capstone --seed 7 --perturb miss-grasp --render --out runs/capstone-pictures
```

`miss-grasp` 让全任务的第一次有效抓取失败，之后恢复正常；`shift-goal` 在第一次成功抓取后把当前蓝色目标移到 `(-0.05,-0.20)`。不能在当前任务未完成或仍持物时切换下一物体。摘要最终同时验证两物体位置、释放状态、中心高度和线速度，避免只检查最后一个任务。

`summary` 含 `success/completed_ids/skipped_duplicates/tool_calls/final_observation`。`final_observation.objects.red/green` 各含 `block_xyz/goal_xyz/linear_speed_m_s/holding/success`；`task.all_success` 是两者同时成立。`memory.json` 保留两个任务的完成证据。事件中的 `active_object` 在 `result.observation` 内。

可选 `--render` 输出真实 `capstone-before.png/capstone-after.png`；默认不创建渲染器。相机里机械臂仍可能遮住已放下的绿色方块，截图不能取代状态验收。种子 7、抓空扰动实测完成两任务，16 次工具调用，复核后跳过 1 次重复请求。

毕业任务集成的是状态、技能、任务历史、目标刷新与失败恢复。第 12 章颜色定位、第 13 章解释器和第 14 章学习策略是独立练习，尚未接入毕业任务动作决策；不要据此声称完成视觉语言动作全栈系统。

## 本次验收

2026-11-06，在 Python 3.12.16、MuJoCo 3.3.7、NumPy 2.2.6、macOS arm64 上实际运行全部七个入口。第一期 7 项与第二期 8 项测试共 15 项通过。新测试覆盖完成记录失效、空间过期/更新、程序全量校验与预算、真实学习 ID/OOD 结果、评测初态匹配，以及种子 0/7/19 × 三种条件的九次双物体任务。主动观察与可选毕业渲染另行实际运行并目视检查 PNG。

没有真实模型请求、网络训练权重或真实机器人运行。所有新增源码与配置集中在 `advanced.py/test_advanced.py/capstone.xml/example-program.json/ADVANCED_GUIDE.md`；第一期文件保持原样。
