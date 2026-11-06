# Agent Fieldnotes：可运行教学实验

这份实验用 MuJoCo 做一个桌面抓放任务：把红色方块放到蓝色区域。它是从状态、坐标、技能到反馈控制的入门环境，与课程第 1–9 章对应。默认离线运行，不需要模型密钥。

## 先理解实验边界

- 机器人是本项目自建的简化 SCARA：两个平面转动关节和一个竖直移动关节。它不是 Panda、工业机械臂模型、VLA 或训练后的策略。
- MuJoCo 实际推进关节动力学、重力、物体接触和释放后的落地过程；抓取用显式 `weld` 约束连接工具与方块。夹爪、连杆不参与碰撞，不能据此证明真实夹持、避障或安全性。
- `baseline` 是固定动作序列，`agent --mode scripted` 是可审阅的确定性反馈状态机；两者都不调用语言模型。这里只用它们比较“忽略反馈”和“根据观测选择下一步”。
- 默认动作循环读取仿真器状态。`vision` 独立提供真实渲染图像和颜色定位练习；它不是视觉动作闭环，也没有 VLM。
- `agent --mode llm` 才会向显式配置的模型端点发起真实请求。我们验证了适配器的预算和错误处理，但未用真实模型验收。不要把离线成功率当作大模型或真实机器人的能力评测。

## 安装与第一轮

在仓库根目录执行。建议 Python 3.12；本次验证为 3.12.16、macOS arm64，依赖固定在 `requirements.txt`。

```bash
python3 -m venv lab/.venv
source lab/.venv/bin/activate
python -m pip install -r lab/requirements.txt
python lab/run.py doctor
python lab/run.py agent --mode scripted --seed 7 --out runs/first
```

Windows 的激活命令是 `lab\.venv\Scripts\activate`。本文剩余命令都在仓库根目录、已激活环境下运行。若不激活环境，macOS/Linux 可直接使用 `lab/.venv/bin/python`。

`doctor` 分别报告 `physics` 与 `render`。物理实验不需要交互窗口；`vision` 需要可用的 OpenGL 渲染环境。渲染失败并不等于物理失败；先记录具体驱动错误，不要把 `render: unavailable` 写成视觉实验已通过。MuJoCo 的 Python 包含引擎本身，安装机制见[官方 Python 文档](https://mujoco.readthedocs.io/en/3.3.7/python.html)。

`runs/first/summary.json` 应有 `mode: scripted`、`model_calls: 0`、`success: true`。`events.jsonl` 每行记录一次技能调用与结果。每次 CLI 命令都会创建一个新场景；连续执行两条 `move` 命令不会延续上一条的位置。

## 从观测到技能

```bash
python lab/run.py observe --seed 7
python lab/run.py move --seed 7 --x -0.05 --y 0.10 --z 0.18 --out runs/move
python lab/run.py baseline --seed 7 --out runs/baseline
```

`observe` 的长度单位是米，`robot.joints_rad` 只包含两个转动关节的弧度，`robot.vertical_slide_m` 是竖直关节位移。工具的位置在 `robot.tool_xyz`，物体中心位置在 `scene.block_xyz`，目标中心位置在 `scene.goal_xyz`，方块线速度大小在 `scene.block_linear_speed_m_s`（米/秒，保留原始浮点精度，可直接检查 `< 0.05` 的成功条件）。这些坐标是 `observation_source: simulator_state` 的仿真状态，不是感知结果。

桌面为世界坐标 `z=0`，机器人基座在 `(-0.4, 0, 0.32)`，平面连杆长 `0.35` 和 `0.30` 米。`move` 用解析逆运动学得到位置伺服目标，再推进 1.4 秒仿真。允许的工具高度是 `[0.045, 0.32]`，最终三维位置误差小于 `0.02` 米才算技能执行成功。低于 `0.12` 米时，横向移动超过 `0.04` 米会被拒绝，先抬高再平移。

本环境的工具接口在 `run.py` 的 `World` 中：

| 接口 | 输入与结果 |
| --- | --- |
| `observe()` | 当前机器人、场景和任务状态 |
| `move(x, y, z)` | 世界坐标米制目标；返回 `ok`、`observation`、可选 `error` |
| `grasp()` | 工具到方块 XY 距离小于 3.5 cm、Z 差小于 5 cm 时启用约束；错误包括 `not_at_block` |
| `release()` | 解除约束并等待 1.2 秒仿真；空夹爪返回 `empty_gripper` |
| `locate_color(kind)` | 从渲染 RGB 定位 `block` 或 `goal`；返回来源及像素支持数 |

命令行没有单独的 `grasp` 子命令。在同一个 Python 进程里调用技能才会共享状态，例如：

```python
from lab.run import World

w = World(seed=7)
print(w.grasp())  # 初始工具没在方块附近，预期 not_at_block
p = w.observe()["scene"]["block_xyz"]
print(w.move(p[0], p[1], 0.18))
print(w.move(p[0], p[1], 0.06))
print(w.grasp())
print(w.observe()["robot"]["holding"])
```

抓取近似的具体物理含义可查[MuJoCo weld 约束](https://mujoco.readthedocs.io/en/3.3.7/XMLreference.html#equality-weld)。本项目在抓取时保存当前工具与方块的相对位姿，并启用该约束。

## 让失败暴露反馈的价值

```bash
python lab/run.py baseline --seed 7 --perturb miss-grasp --out runs/miss-baseline
python lab/run.py agent --mode scripted --seed 7 --perturb miss-grasp --out runs/miss-agent
python lab/run.py baseline --seed 7 --perturb shift-goal --out runs/shift-baseline
python lab/run.py agent --mode scripted --seed 7 --perturb shift-goal --out runs/shift-agent
python lab/run.py evaluate --seeds 5 --out runs/evaluation
```

`miss-grasp` 在第一次满足抓取前置条件时返回 `injected_miss_grasp`，不建立连接；下一次允许正常抓取。`shift-goal` 在第一次成功抓取后，把目标移到 `(0.08, 0.20)`，新的位置会出现在返回的观测中。它们是人为控制的教学扰动，不是随机真实故障分布。

固定基线只使用最初的目标坐标，且不根据技能失败修改序列。状态机每步重新观测，最多执行 32 个动作。任务成功需要：已经释放、方块与当前目标 XY 距离小于 4.5 cm、中心高度在 `(0.015, 0.065)` 米、线速度小于 `0.05 m/s`。技能 `ok: true` 本身不能替代任务验收。

`baseline`、`agent` 和 `move` 成功时退出码为 0，失败为 2。故障基线的退出码 2 是预期实验结果，不代表程序崩溃。`evaluate` 会完成全部对照并返回 0；请读取每回合的 `success`。`--seeds 5` 对应种子 0–4，三个扰动条件、两种策略，共 30 回合。

## 目标解析与受控视觉

```bash
python lab/run.py parse-goal --instruction '把红色方块放到蓝色区域'
python lab/run.py parse-goal --instruction '不要把红色方块放到蓝色区域'
python lab/run.py vision --seed 7 --out runs/vision
```

目标解析器是全文模板匹配。它接受“把/请把/将红色方块放到蓝色区域”及代码中列出的两个英文模板，忽略大小写、空白和末尾常见标点。其他表达返回 `needs_clarification`，不会仅凭句中出现红色和蓝色就执行。独立 `parse-goal` 用输出状态表达澄清需求；`agent` 遇到它则以退出码 2 停止。

`vision` 写出 `top-camera.png` 和 `vision.json`。`locate_color` 从真实 RGB 图像做红/蓝阈值分割，取像素中位数，并利用已知相机参数与已知水平表面高度做射线平面求交；函数不读取物体真值坐标来生成定位结果。它假定固定俯视相机、已知颜色、已知物体表面高度，返回的 `xyz.z` 是表面而非物体中心。

初始机械臂可能遮挡红块。种子 7 的本机运行中，检测返回 `ok: true`，红块 XY 定位误差仍约 1.61 cm，蓝色目标约 0.16 cm。这正好用于区分“检测到颜色”和“位置足够准确”。改变光照、遮挡、物体高度或相机后，必须重新验证这些假设。

## 可选的真实模型模式

仅在你准备好端点和调用预算后运行。模型服务需要兼容 Chat Completions 的函数工具调用；配置的 base URL 应包含提供方要求的版本前缀，程序会追加 `/chat/completions`。密钥只从环境变量读取。下面的值都是占位符：

```bash
export AF_BASE_URL='https://YOUR-ENDPOINT/v1'
export AF_MODEL='YOUR-TOOL-CALLING-MODEL'
# 在当前终端安全地设置 AF_API_KEY，勿写入仓库或截图。
python lab/run.py agent --mode llm --max-calls 12 --seed 7 --out runs/llm
```

默认最多 12 次 HTTP 请求，可设 1–50；每次响应 `max_tokens` 为 700、超时为 60 秒，每个响应最多执行 8 个工具动作。这是调用次数与单次输出上限，不是金额上限，输入上下文会逐步增长。远程端点须 HTTPS，本机回环地址可用 HTTP。没有密钥时程序明确失败，不会悄悄回退为 scripted。

在线模式能调用 `observe/move/grasp/release`，接收仿真状态与工具结果。它仍受限于同一个固定目标解析器，且不接收图像。输出目录增加 `model-messages.json`；发生请求错误时也保存已经形成的对话。日志不写请求密钥或 Authorization 头，但会包含任务与模型回复。失败摘要 `model_calls` 记录已尝试的请求数，不代表服务端计费结算数。

## 回归检查与文件

```bash
python -m unittest discover -s lab -p 'test_*.py' -v
```

检查覆盖真实物理结果、扰动恢复、无效移动不修改场景、空抓取、否定指令拒绝、日志来源，以及使用无网络 mock 的模型请求预算和错误路径。图像渲染单独通过 `doctor/vision` 检查，避免无显示环境把纯物理回归误判为失败。

每个运行使用独立 `--out` 目录，因为同一路径会覆盖旧文件。`events.jsonl` 字段是 `step/sim_time_s/tool/arguments/result`；`summary.json` 包含 `mode/seed/perturb/success/steps/model_calls/error/observation_source/grasp_model/final_observation`。`step` 从 0 开始；`steps` 是记录的工具事件数，仿真时间不等于实际运行用时。具体实测记录见 [VALIDATION.md](VALIDATION.md)。
