#!/usr/bin/env python3
"""Record real teaching-world trajectories without changing the controllers.

From the repository root, use the lab environment and install imageio-ffmpeg==0.6.0.
Only the authoring tool needs the encoder; the student experiment package does not.
"""
from pathlib import Path
import json
import hashlib
import sys
import tempfile

import imageio_ffmpeg
import mujoco
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from lab.run import World, baseline, scripted_agent, png_bytes
from lab.advanced import TwoObjectWorld, TaskMemory, feedback_controller

OUT = ROOT / "docs/course-media"
FPS = 20


def timestamp(seconds):
    milliseconds = round(seconds * 1000)
    h, milliseconds = divmod(milliseconds, 3600000)
    m, milliseconds = divmod(milliseconds, 60000)
    s, milliseconds = divmod(milliseconds, 1000)
    return f"{h:02}:{m:02}:{s:02}.{milliseconds:03}"


class Recorder:
    def __init__(self, world, key):
        self.world, self.key = world, key
        self.frames, self.cues = 0, []
        self.initial = world.observe()
        self.renderer = mujoco.Renderer(world.model, height=480, width=640)
        self.writer = imageio_ffmpeg.write_frames(
            str(OUT / f"{key}.mp4"), (640, 480), fps=FPS,
            codec="libx264", pix_fmt_out="yuv420p", quality=7,
            output_params=["-movflags", "+faststart"], ffmpeg_log_level="error",
        )
        self.writer.send(None)
        (OUT / f"{key}.png").write_bytes(png_bytes(self.frame()))
        self.hold("初始场景：红块 → 蓝区" if key != "course-capstone"
                  else "初始场景：红块 → 蓝区；绿块 → 黄区", 1, phase="milestone")

    @property
    def time(self):
        return self.frames / FPS

    def frame(self):
        self.renderer.update_scene(self.world.data, camera="top")
        return self.renderer.render().copy()

    def capture(self):
        self.writer.send(self.frame())
        self.frames += 1

    def hold(self, text, duration=0.7, phase="result"):
        start = self.time
        frame = self.frame()
        for _ in range(round(duration * FPS)):
            self.writer.send(frame)
            self.frames += 1
        self.cues.append({"start": start, "end": self.time, "text": text, "phase": phase})

    def action(self, name, function, args):
        start = self.time
        result = function(*args)
        label = {"move": "移动", "grasp": "抓取", "release": "释放"}[name]
        if args:
            label += "：目标 (" + ", ".join(f"{v:.3f}" for v in args) + ") m"
        if hasattr(self.world, "active"):
            label = ("红块" if self.world.active == "red" else "绿块") + " · " + label
        if self.time > start:
            self.cues.append({"start": start, "end": self.time, "text": label, "phase": "action"})
        state = "holding=true" if self.world.holding else "holding=false"
        outcome = "ok=true" if result["ok"] else "失败：" + result.get("error", "unknown")
        # Hold the real final frame for readability, without advancing physics.
        self.hold(f"{label} → {outcome}；{state}", 0.8 if result["ok"] else 1.5)
        return result

    def close(self, success, extra=None):
        self.hold("最终验收：" + ("通过" if success else "未通过"), 1.5, phase="milestone")
        self.writer.close()
        self.renderer.close()
        transcript = {"key": self.key, "seed": self.world.seed,
                      "perturb": self.world.perturb, "model_calls": 0,
                      "success": success, "duration_s": self.time, "fps": FPS,
                      "capture": "real MuJoCo frames at simulation speed; frozen review pauses between skills; no audio",
                      "versions": {"mujoco": mujoco.__version__, "numpy": np.__version__, "imageio_ffmpeg": imageio_ffmpeg.__version__},
                      "source_sha256": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in [ROOT/"lab/run.py", ROOT/"lab/advanced.py", ROOT/"lab/scene.xml", ROOT/"lab/capstone.xml", Path(__file__).resolve()]},
                      "initial_observation": self.initial,
                      "final_observation": self.world.observe(),
                      "events": self.world.events, "cues": self.cues, **(extra or {})}
        (OUT / f"{self.key}.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2))
        vtt = "WEBVTT\n\n" + "\n\n".join(
            f"{timestamp(c['start'])} --> {timestamp(c['end'])}\n{c['text']}" for c in self.cues)
        (OUT / f"{self.key}.vtt").write_text(vtt + "\n")
        print(self.key, "success=", success, "calls=", len(self.world.events), "seconds=", self.time)


class RecordingMixin:
    recorder = None

    def step(self, n):
        if self.recorder is None:
            return super().step(n)
        # The model timestep is 0.002 s: 25 physics steps per 20 fps video frame.
        stride = round(1 / (FPS * self.model.opt.timestep))
        for i in range(n):
            mujoco.mj_step(self.model, self.data)
            if (i + 1) % stride == 0:
                self.recorder.capture()

    def move(self, x, y, z):
        return self.recorder.action("move", super().move, (x, y, z))

    def grasp(self):
        return self.recorder.action("grasp", super().grasp, ())

    def release(self):
        return self.recorder.action("release", super().release, ())


class RecordedWorld(RecordingMixin, World):
    pass


class RecordedTwoObjectWorld(RecordingMixin, TwoObjectWorld):
    pass


def record_single(key, controller, perturb):
    world = RecordedWorld(seed=7, perturb=perturb)
    world.recorder = Recorder(world, key)
    controller(world)
    world.recorder.close(world.success(), {"controller": controller.__name__})


def record_capstone():
    world = RecordedTwoObjectWorld(seed=7, perturb="miss-grasp")
    world.recorder = Recorder(world, "course-capstone")
    memory, skipped = TaskMemory(), 0
    for name in ("red", "green", "red"):
        world.active = name
        task_id = name + "_to_" + ("blue" if name == "red" else "yellow")
        if memory.skip_completed(task_id, world):
            skipped += 1
            world.recorder.hold("重复请求：重新核对红块位置，仍然完成，跳过搬运", 2, phase="milestone")
            continue
        feedback_controller(world)
        if not memory.remember(task_id, world):
            break
    world.recorder.close(world.observe()["task"]["all_success"],
                         {"skipped_duplicates": skipped, "memory": memory.dump(),
                          "controller": "feedback_controller with TaskMemory and red/green/red scheduler"})


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    destination = OUT
    # Do not replace published artifacts until every recording has completed.
    # The manifest is replaced last: an interrupted copy fails the build hash check.
    with tempfile.TemporaryDirectory(prefix=".recording-", dir=destination) as temporary:
        OUT = Path(temporary)
        record_single("course-baseline", baseline, "none")
        record_single("course-recovery", scripted_agent, "miss-grasp")
        record_single("course-shift-baseline", baseline, "shift-goal")
        record_single("course-shift-feedback", scripted_agent, "shift-goal")
        record_capstone()
        manifest = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.iterdir())}
        for name in manifest:
            (OUT/name).replace(destination/name)
        manifest_path = OUT/"recordings-manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        manifest_path.replace(destination/manifest_path.name)
