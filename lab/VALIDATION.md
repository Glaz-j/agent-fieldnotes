# 本机验收记录

验证日期：2026-11-06。此记录只描述本次实际运行，不承诺所有平台或真实机器人上的行为。

环境：Python 3.12.16，MuJoCo 3.3.7，NumPy 2.2.6，macOS 26.6 arm64。仓库根目录执行 `lab/.venv/bin/python`，以下用 `python` 简写同一个解释器。

| 命令 | 结果 |
| --- | --- |
| `python lab/run.py doctor` | `physics: ok`，`render: ok` |
| `python lab/run.py agent --mode scripted --seed 7 --out lab/runs/test` | `success: true`，7 个工具事件，0 次模型调用 |
| `python lab/run.py evaluate --seeds 5 --out lab/runs/evaluation` | 实际完成 30 个 MuJoCo 回合，结果如下 |
| `python lab/run.py vision --seed 7 --out lab/runs/vision` | 实际生成 640×480 RGB PNG 和颜色定位 JSON |
| `python -m unittest discover -s lab -p 'test_*.py' -v` | 7 项测试通过；包括多种种子的物理回合与无网络协议测试 |

30 回合的成功数：

| 扰动 | 固定基线 | 确定性反馈状态机 |
| --- | --- | --- |
| none | 5 / 5 | 5 / 5 |
| miss-grasp | 0 / 5 | 5 / 5 |
| shift-goal | 0 / 5 | 5 / 5 |

种子为 0–4。测试专门构造了一次抓空和一次目标移动，说明当前环境中反馈逻辑的作用，不是通用机器人能力、大模型能力或统计充分的基准评测。

种子 7 的视觉输出中，红色像素数 75，估计表面位置 `[-0.05408, 0.122, 0.044]`；蓝色像素数 2990，估计表面位置 `[0.08099, -0.17870, 0.014]`。红块受到机械臂部分遮挡，与独立读取的仿真真值比较，XY 误差约 0.0161 米；目标 XY 误差约 0.00163 米。该定位结果没有用于动作循环，不能据此宣称完成视觉闭环。

在线模型模式只测试了本地适配器的请求次数上限、错误日志、密钥不落盘和远程 HTTP 拒绝。未向真实模型发送请求，因此没有模型成功率、真实 token 消耗或真实服务兼容性结论。

模型范围：自建 SCARA，显式焊接约束近似抓取，连杆与夹爪不做碰撞验证。验收读取仿真状态。完整说明与复跑命令见 [GUIDE.md](GUIDE.md)。
