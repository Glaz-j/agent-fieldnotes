#!/usr/bin/env python3
"""Lessons 10–16: bounded, inspectable experiments. See ADVANCED_GUIDE.md."""
from __future__ import annotations
import argparse
import copy
import json
import math
from pathlib import Path
import sys

import mujoco
import numpy as np
if __package__:
    from .run import World, baseline, png_bytes, scripted_agent
else:
    from run import World, baseline, png_bytes, scripted_agent

BASE = Path(__file__).resolve().parent


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2))


def finish(out, summary, events=()):
    out.mkdir(parents=True, exist_ok=True)
    summary = {"model_calls": 0, **summary}
    write_json(out / "summary.json", summary)
    (out / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in events))
    return summary


class TaskMemory:
    """Completion evidence is a record, never a substitute for current verification."""
    def __init__(self):
        self.completed = {}
        self.events = []

    def skip_completed(self, task_id, w):
        if task_id not in self.completed:
            return False
        valid = w.success()
        self.events.append({"event": "revalidate_completion", "task_id": task_id,
                            "at_sim_time_s": float(w.data.time), "valid_now": valid})
        if not valid:
            del self.completed[task_id]
        return valid

    def remember(self, task_id, w):
        if not w.success():
            return False
        evidence = {"source": "simulator_state", "at_sim_time_s": float(w.data.time),
                    "observation": w.observe()}
        self.completed[task_id] = evidence
        self.events.append({"event": "completed", "task_id": task_id, "evidence": evidence})
        return True

    def dump(self):
        return {"completed": self.completed, "events": self.events}


def memory_experiment(seed, out):
    w, memory = World(seed), TaskMemory()
    requests = ["red_to_blue", "red_to_blue"]
    skipped = 0
    for task_id in requests:
        if memory.skip_completed(task_id, w):
            skipped += 1
            continue
        scripted_agent(w)
        memory.remember(task_id, w)
    write_json(out / "memory.json", memory.dump())
    return finish(out, {"experiment": "memory", "seed": seed, "requests": requests,
                       "completed_ids": list(memory.completed), "skipped_duplicates": skipped,
                       "action_calls": len(w.events), "success": w.success()}, w.events)


class SpatialMemory:
    def __init__(self):
        self.records = []

    def observe(self, xyz, now, source="simulator_state"):
        changed = bool(self.records and np.linalg.norm(np.array(self.records[-1]["xyz"])-xyz) > .01)
        if self.records and self.records[-1]["valid"]:
            old = self.records[-1]
            old["valid"] = False
            old["invalidated_at_s"] = now
            old["reason"] = "position_changed" if changed else "superseded"
        self.records.append({"entity": "blue_goal", "xyz": list(xyz), "source": source,
                             "observed_at_s": now, "valid": True,
                             "update_reason": "position_changed" if changed else "observation"})
        return self.records[-1]

    def lookup(self, now, max_age_s=2.0):
        if not self.records or not self.records[-1]["valid"]:
            return None
        old = self.records[-1]
        if now - old["observed_at_s"] > max_age_s:
            old.update(valid=False, invalidated_at_s=now, reason="expired")
            return None
        return copy.deepcopy(old)


def spatial_experiment(seed, out):
    cases, histories, events = [], {}, []
    for mode in ("stale", "refresh"):
        w, memory = World(seed, "shift-goal"), SpatialMemory()
        old = memory.observe(w.goal.tolist(), float(w.data.time))
        cached_xyz = old["xyz"][:]
        p = w.block
        for xyz in ((p[0], p[1], .18), (p[0], p[1], .06)):
            w.move(*xyz)
        w.grasp()  # This injected event really moves the goal body in MuJoCo.
        expired = memory.lookup(float(w.data.time)) is None
        if mode == "refresh":
            current = memory.observe(w.goal.tolist(), float(w.data.time))
            target = current["xyz"]
        else:
            target = cached_xyz  # Deliberate ablation: ignore expiry and use a stale copy.
        w.move(w.tool[0], w.tool[1], .18)
        w.move(target[0], target[1], .18)
        w.move(target[0], target[1], .065)
        w.release()
        cases.append({"mode": mode, "success": w.success(), "cache_expired": expired,
                      "used_goal_xyz": target, "final_observation": w.observe()})
        histories[mode] = memory.records
        events.extend({"case": mode, **e} for e in w.events)
    write_json(out / "spatial-memory.json", histories)
    return finish(out, {"experiment": "spatial", "seed": seed, "cases": cases}, events)


def active_view_experiment(seed, out):
    w = World(seed)
    def measure(label):
        (out / (label + ".png")).write_bytes(png_bytes(w.render()))
        detection = w.locate_color("block")
        estimate = detection.get("xyz")
        return {"pixels": detection.get("pixels", 0), "estimate_xyz": estimate,
                "xy_error_m": float(np.linalg.norm(np.array(estimate[:2])-w.block[:2])) if estimate else None,
                "detection": detection, "truth_xyz_for_evaluation_only": w.block.tolist()}
    before = measure("before")
    move = w.move(.05, -.23, .24)  # Fixed observation action; no hidden-pose-based viewpoint search.
    after = measure("after")
    return finish(out, {"experiment": "active-view", "seed": seed, "before": before,
                       "after": after, "observation_action_ok": move["ok"],
                       "scope": "move arm out of view; fixed camera; no visual grasp loop"}, w.events)


TOOLS = {"observe", "move", "grasp", "release"}
CONDITIONS = {"holding", "not_holding", "success", "not_success", "last_ok"}
REFERENCES = {f"{entity}.{axis}" for entity in ("block", "goal", "tool") for axis in ("x", "y")}


def validate_program(document):
    if not isinstance(document, dict) or set(document) != {"version", "steps"} or type(document["version"]) is not int or document["version"] != 1:
        raise ValueError("program requires exactly version=1 and steps")
    count = 0
    def check(steps, depth):
        nonlocal count
        if not isinstance(steps, list) or depth > 6:
            raise ValueError("steps must be a list; nesting depth <= 6")
        for node in steps:
            count += 1
            if count > 128 or not isinstance(node, dict):
                raise ValueError("at most 128 object nodes")
            if "call" in node:
                if set(node) - {"call", "args"} or not isinstance(node["call"], str) or node["call"] not in TOOLS:
                    raise ValueError("unknown call or node fields")
                args = node.get("args", {})
                if not isinstance(args, dict) or set(args) != ({"x", "y", "z"} if node["call"] == "move" else set()):
                    raise ValueError("invalid tool arguments")
                for value in args.values():
                    if not ((isinstance(value, str) and value in REFERENCES) or (type(value) in (int, float) and math.isfinite(value))):
                        raise ValueError("coordinates require finite numbers or approved references")
            elif "if" in node:
                if set(node) - {"if", "then", "else"} or "then" not in node or not isinstance(node["if"], str) or node["if"] not in CONDITIONS:
                    raise ValueError("invalid condition")
                check(node["then"], depth + 1)
                check(node.get("else", []), depth + 1)
            elif "repeat" in node:
                if set(node) != {"repeat", "steps"} or type(node["repeat"]) is not int or not 1 <= node["repeat"] <= 16:
                    raise ValueError("repeat requires integer 1..16 and steps")
                check(node["steps"], depth + 1)
            else:
                raise ValueError("unknown program node")
    check(document["steps"], 1)
    return count


def execute_program(w, document, budget=64):
    validate_program(document)  # Entire program checked before any action, even unused branches.
    if not 1 <= budget <= 512:
        raise ValueError("budget must be 1..512")
    executed, last_ok = 0, True
    def resolve(value):
        if isinstance(value, str):
            entity, axis = value.split(".")
            return float(getattr(w, entity)[0 if axis == "x" else 1])
        return value
    def run_nodes(nodes):
        nonlocal executed, last_ok
        for node in nodes:
            if executed >= budget:
                raise RuntimeError("program_budget_exhausted")
            executed += 1
            if "call" in node:
                result = w.call(node["call"], {k: resolve(v) for k,v in node.get("args", {}).items()})
                last_ok = result["ok"]
            elif "if" in node:
                conditions = {"holding": w.holding, "not_holding": not w.holding,
                              "success": w.success(), "not_success": not w.success(), "last_ok": last_ok}
                run_nodes(node["then"] if conditions[node["if"]] else node.get("else", []))
            else:
                for _ in range(node["repeat"]):
                    run_nodes(node["steps"])
    error = None
    try:
        run_nodes(document["steps"])
    except RuntimeError as exc:
        error = str(exc)
    return {"executed_nodes": executed, "budget": budget, "error": error,
            "success": w.success(), "tool_calls": len(w.events)}


def program_experiment(seed, out, path, budget, perturb):
    if path.stat().st_size > 65536:
        raise ValueError("program file must be <= 64 KiB")
    document = json.loads(path.read_text())
    validate_program(document)
    w = World(seed, perturb)
    result = execute_program(w, document, budget)
    write_json(out / "program.json", document)
    return finish(out, {"experiment": "program", "seed": seed, "perturb": perturb,
                       **result, "final_observation": w.observe()}, w.events)


def expert_ik(xy):
    dx, dy = xy[:, 0] + .4, xy[:, 1]
    q2 = np.arccos((dx*dx + dy*dy - .35**2 - .30**2) / (2*.35*.30))
    q1 = np.arctan2(dy, dx) - np.arctan2(.30*np.sin(q2), .35+.30*np.cos(q2))
    return np.column_stack((q1, q2))


def features(xy, mean, scale):
    x, y = ((xy-mean)/scale).T
    return np.column_stack((np.ones_like(x), x, y, x*x, x*y, y*y))


def learned_skill_experiment(seed, out):
    rng = np.random.default_rng(seed)
    low, high = np.array([-.14, .02]), np.array([-.02, .14])
    train = rng.uniform(low, high, (80, 2))
    tests = {"id": rng.uniform(low, high, (20, 2)),
             "ood": rng.uniform([0, -.24], [.15, -.12], (20, 2))}
    mean, scale = train.mean(axis=0), train.std(axis=0)
    labels = expert_ik(train)
    weights = np.linalg.lstsq(features(train, mean, scale), labels, rcond=None)[0]
    write_json(out / "weights.json", {"feature_order": ["1", "x", "y", "x*x", "x*y", "y*y"],
                                      "mean_xy": mean.tolist(), "scale_xy": scale.tolist(),
                                      "weights": weights.tolist(), "output": "q1,q2 radians"})
    write_json(out / "dataset.json", {"seed": seed, "train_xy": train.tolist(), "train_q": labels.tolist(),
                                      "test_xy": {k:v.tolist() for k,v in tests.items()}})
    rows = []
    for split, xy in tests.items():
        predictions = features(xy, mean, scale) @ weights
        for policy, targets in (("learned", predictions), ("analytic", expert_ik(xy))):
            for i, (p, q) in enumerate(zip(xy, targets)):
                w = World(seed)
                bounded = np.clip(q, -3.14, 3.14)
                w.data.ctrl[:] = [bounded[0], bounded[1], .18-.32]
                w.step(700)  # Learned q really drives MuJoCo's servo actuators.
                error = float(np.linalg.norm(w.tool - [p[0], p[1], .18]))
                rows.append({"split": split, "policy": policy, "sample": i,
                             "target_xyz": [*p.tolist(), .18], "predicted_joints_rad": q.tolist(),
                             "clipped": bool(np.any(bounded != q)), "reached_xyz": w.tool.tolist(),
                             "position_error_m": error, "success": error < .02})
    write_json(out / "reach-results.json", rows)
    groups = []
    for split in tests:
        for policy in ("learned", "analytic"):
            group = [r for r in rows if r["split"] == split and r["policy"] == policy]
            groups.append({"split": split, "policy": policy, "samples": len(group),
                           "successes": sum(r["success"] for r in group),
                           "mean_position_error_m": float(np.mean([r["position_error_m"] for r in group]))})
    return finish(out, {"experiment": "learned-skill", "seed": seed, "train_samples": 80,
                       "groups": groups, "scope": "supervised local IK approximation; no VLA or learned grasp"})


def feedback_controller(w, retry=True, refresh=True, max_steps=32):
    cached_goal = w.goal.copy()
    for _ in range(max_steps):
        if w.success():
            break
        p, t = w.block, w.tool
        g = w.goal if refresh else cached_goal
        if w.holding:
            if np.linalg.norm(t[:2]-g[:2]) > .025:
                target = [t[0], t[1], .18] if t[2] < .12 else [g[0], g[1], .18]
                result = w.move(*target)
            elif t[2] > .09:
                result = w.move(g[0], g[1], .065)
            else:
                result = w.release()
        elif np.linalg.norm(t[:2]-p[:2]) > .025:
            target = [t[0], t[1], .18] if t[2] < .12 else [p[0], p[1], .18]
            result = w.move(*target)
        elif t[2] > .085:
            result = w.move(p[0], p[1], .06)
        else:
            result = w.grasp()
        if not retry and not result["ok"]:
            break


def benchmark_experiment(seeds, out):
    rows, events = [], []
    policies = ("baseline", "feedback", "no-retry", "stale-spatial")
    for seed in range(seeds):
        for perturb in ("none", "miss-grasp", "shift-goal"):
            for policy in policies:
                w = World(seed, perturb)
                initial = w.observe()
                if policy == "baseline":
                    baseline(w)
                else:
                    feedback_controller(w, retry=policy != "no-retry", refresh=policy != "stale-spatial")
                rows.append({"seed": seed, "perturb": perturb, "policy": policy, "success": w.success(),
                             "tool_calls": len(w.events), "initial_observation": initial,
                             "final_observation": w.observe()})
                events.extend({"seed": seed, "perturb": perturb, "policy": policy, **e} for e in w.events)
    groups = []
    for perturb in ("none", "miss-grasp", "shift-goal"):
        for policy in policies:
            group = [r for r in rows if r["perturb"] == perturb and r["policy"] == policy]
            groups.append({"perturb": perturb, "policy": policy, "episodes": len(group),
                           "successes": sum(r["success"] for r in group),
                           "mean_tool_calls": float(np.mean([r["tool_calls"] for r in group]))})
    write_json(out / "episodes.json", rows)
    return finish(out, {"experiment": "benchmark", "seeds": list(range(seeds)),
                       "episodes": len(rows), "groups": groups}, events)


class TwoObjectWorld(World):
    """Original SCARA with two actual free bodies and two independent welds."""
    OBJECTS = {"red": ("block", "goal", "block_free", 0),
               "green": ("block2", "goal2", "block2_free", 1)}

    def __init__(self, seed=7, perturb="miss-grasp"):
        self.model = mujoco.MjModel.from_xml_path(str(BASE / "capstone.xml"))
        self.data = mujoco.MjData(self.model)
        self.seed, self.perturb, self.active = seed, perturb, "red"
        self.events, self.injected, self.model_calls = [], False, 0
        self.data.qpos[:3] = [0, 1.7, 0]
        rng = np.random.default_rng(seed)
        for name, center in (("red", [-.10, .10]), ("green", [-.12, -.09])):
            adr = self.model.joint(self.OBJECTS[name][2]).qposadr[0]
            self.data.qpos[adr:adr+3] = [*(np.array(center)+rng.uniform(-.025,.025,2)), .025]
            self.data.qpos[adr+3:adr+7] = [1, 0, 0, 0]
        self.data.ctrl[:] = self.data.qpos[:3]
        mujoco.mj_forward(self.model, self.data)
        self.step(500)

    @property
    def block(self):
        return self.data.body(self.OBJECTS[self.active][0]).xpos.copy()

    @property
    def goal(self):
        return self.data.body(self.OBJECTS[self.active][1]).xpos.copy()

    @property
    def holding(self):
        return bool(np.any(self.data.eq_active))

    def object_state(self, name):
        block, goal, joint, eq = self.OBJECTS[name]
        p, g = self.data.body(block).xpos, self.data.body(goal).xpos
        adr = self.model.joint(joint).dofadr[0]
        speed = float(np.linalg.norm(self.data.qvel[adr:adr+3]))
        success = bool(not self.data.eq_active[eq] and np.linalg.norm(p[:2]-g[:2]) < .045 and .015 < p[2] < .065 and speed < .05)
        return {"block_xyz": p.tolist(), "goal_xyz": g.tolist(), "linear_speed_m_s": speed,
                "holding": bool(self.data.eq_active[eq]), "success": success}

    def success(self):
        return self.object_state(self.active)["success"]

    def observe(self):
        obs = super().observe()
        obs["active_object"] = self.active
        obs["objects"] = {name: self.object_state(name) for name in self.OBJECTS}
        obs["scene"]["block_linear_speed_m_s"] = obs["objects"][self.active]["linear_speed_m_s"]
        obs["task"]["all_success"] = all(s["success"] for s in obs["objects"].values())
        return obs

    def grasp(self):
        if self.holding:
            return self.result("grasp", {}, False, "already_holding")
        if np.linalg.norm(self.tool[:2]-self.block[:2]) >= .035 or abs(self.tool[2]-self.block[2]) >= .05:
            return self.result("grasp", {}, False, "not_at_block")
        if self.perturb == "miss-grasp" and not self.injected:
            self.injected = True
            return self.result("grasp", {}, False, "injected_miss_grasp")
        block, goal, _, eq = self.OBJECTS[self.active]
        rotation = self.data.body("tool").xmat.reshape(3,3)
        self.model.eq_data[eq,3:6] = rotation.T @ (self.block-self.tool)
        qinv = self.data.body("tool").xquat.copy()
        qinv[1:] *= -1
        qrel = np.zeros(4)
        mujoco.mju_mulQuat(qrel, qinv, self.data.body(block).xquat)
        self.model.eq_data[eq,6:10] = qrel
        self.data.eq_active[eq] = 1
        self.step(100)
        if self.perturb == "shift-goal" and not self.injected:
            self.injected = True
            mocap = self.model.body(goal).mocapid[0]
            self.data.mocap_pos[mocap,:2] = [-.05, -.20]
            mujoco.mj_forward(self.model, self.data)
        return self.result("grasp", {})

    def release(self):
        if not self.holding:
            return self.result("release", {}, False, "empty_gripper")
        self.data.eq_active[:] = 0
        self.step(600)
        return self.result("release", {})


def capstone_experiment(seed, out, perturb, render=False):
    w, memory = TwoObjectWorld(seed, perturb), TaskMemory()
    if render:
        (out / "capstone-before.png").write_bytes(png_bytes(w.render()))
    requests, skipped = ["red", "green", "red"], 0
    for name in requests:
        w.active = name
        task_id = name + "_to_" + ("blue" if name == "red" else "yellow")
        if memory.skip_completed(task_id, w):
            skipped += 1
            continue
        feedback_controller(w)
        if not memory.remember(task_id, w):
            break  # Do not switch objects while the current task is unfinished/holding.
    write_json(out / "memory.json", memory.dump())
    final = w.observe()
    if render:
        (out / "capstone-after.png").write_bytes(png_bytes(w.render()))
    return finish(out, {"experiment": "capstone", "seed": seed, "perturb": perturb,
                       "success": final["task"]["all_success"], "completed_ids": list(memory.completed),
                       "skipped_duplicates": skipped, "tool_calls": len(w.events),
                       "final_observation": final,
                       "scope": "two physical objects; state-based feedback and completion memory; weld grasp"}, w.events)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["memory", "spatial", "active-view", "program", "learned-skill", "benchmark", "capstone"])
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", type=Path, default=Path("runs/advanced"))
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--program", type=Path, default=BASE / "example-program.json")
    parser.add_argument("--budget", type=int, default=64)
    parser.add_argument("--render", action="store_true", help="save before/after RGB for capstone only")
    parser.add_argument("--perturb", choices=["none", "miss-grasp", "shift-goal"], default="miss-grasp")
    args = parser.parse_args()
    if not 1 <= args.seeds <= 100:
        parser.error("--seeds must be 1..100")
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        if args.command == "program":
            result = program_experiment(args.seed, args.out, args.program, args.budget, args.perturb)
        elif args.command == "benchmark":
            result = benchmark_experiment(args.seeds, args.out)
        elif args.command == "capstone":
            result = capstone_experiment(args.seed, args.out, args.perturb, args.render)
        else:
            functions = {"memory": memory_experiment, "spatial": spatial_experiment,
                         "active-view": active_view_experiment, "learned-skill": learned_skill_experiment}
            result = functions[args.command](args.seed, args.out)
    except (ValueError, RuntimeError, OSError) as exc:
        result = finish(args.out, {"experiment": args.command, "error": type(exc).__name__ + ": " + str(exc), "success": False})
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(2 if result.get("error") or result.get("success") is False else 0)


if __name__ == "__main__":
    main()
