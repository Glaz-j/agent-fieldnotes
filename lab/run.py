#!/usr/bin/env python3
"""Explicitly simplified SCARA teaching lab; see GUIDE.md for model boundaries."""
from __future__ import annotations
import argparse
import json
import math
import os
from pathlib import Path
import platform
import struct
import sys
import urllib.request
from urllib.parse import urlsplit
import zlib

import mujoco
import numpy as np

BASE = Path(__file__).resolve().parent
DEFAULT_GOAL = "把红色方块放到蓝色区域"


def rounded(v):
    return np.asarray(v).round(5).tolist()


def parse_goal(instruction):
    # This is a deliberately narrow rule parser, not language-model reasoning.
    normalized = "".join(instruction.lower().strip().split()).rstrip("。.!！")
    supported = {"把红色方块放到蓝色区域", "请把红色方块放到蓝色区域", "将红色方块放到蓝色区域", "puttheredblockinthebluearea", "movetheredblocktothebluearea"}
    if normalized not in supported:
        return {"status": "needs_clarification", "question": "当前教学解析器仅接受明确模板，例如：把红色方块放到蓝色区域。请确认目标。", "parser": "restricted_rules"}
    return {"status": "ready", "object": "red_block", "target": "blue_goal", "parser": "restricted_rules"}


class World:
    def __init__(self, seed=7, perturb="none"):
        self.model = mujoco.MjModel.from_xml_path(str(BASE / "scene.xml"))
        self.data = mujoco.MjData(self.model)
        self.seed, self.perturb = seed, perturb
        self.events, self.injected = [], False
        self.model_calls = 0
        self.data.qpos[:3] = [0, 1.7, 0]
        rng = np.random.default_rng(seed)
        self.data.qpos[3:6] = [-0.08 + rng.uniform(-0.04, 0.04), 0.08 + rng.uniform(-0.05, 0.05), 0.025]
        self.data.qpos[6:10] = [1, 0, 0, 0]
        self.data.ctrl[:] = self.data.qpos[:3]
        mujoco.mj_forward(self.model, self.data)
        self.step(500)

    def step(self, n):
        for _ in range(n):
            mujoco.mj_step(self.model, self.data)

    @property
    def block(self):
        return self.data.body("block").xpos.copy()

    @property
    def goal(self):
        return self.data.body("goal").xpos.copy()

    @property
    def tool(self):
        return self.data.body("tool").xpos.copy()

    @property
    def holding(self):
        return bool(self.data.eq_active[0])

    def success(self):
        return bool(not self.holding and np.linalg.norm(self.block[:2] - self.goal[:2]) < 0.045 and 0.015 < self.block[2] < 0.065 and np.linalg.norm(self.data.qvel[3:6]) < 0.05)

    def observe(self):
        return {"observation_source": "simulator_state", "robot": {"joints_rad": rounded(self.data.qpos[:2]), "vertical_slide_m": round(float(self.data.qpos[2]), 5), "tool_xyz": rounded(self.tool), "holding": self.holding}, "scene": {"block_xyz": rounded(self.block), "goal_xyz": rounded(self.goal), "block_linear_speed_m_s": float(np.linalg.norm(self.data.qvel[3:6]))}, "task": {"success": self.success()}}

    def result(self, name, args, ok=True, error=None):
        r = {"ok": ok, "observation": self.observe()}
        if error:
            r["error"] = error
        self.events.append({"step": len(self.events), "sim_time_s": round(self.data.time, 3), "tool": name, "arguments": args, "result": r})
        return r

    def move(self, x, y, z):
        args = {"x": x, "y": y, "z": z}
        if not all(isinstance(v, (int, float)) and math.isfinite(v) for v in args.values()):
            return self.result("move", args, False, "invalid_coordinates")
        dx, dy = x + 0.4, y
        c = (dx*dx + dy*dy - 0.35**2 - 0.30**2) / (2*0.35*0.30)
        if not -1 <= c <= 1 or not 0.045 <= z <= 0.32:
            return self.result("move", args, False, "unreachable")
        if self.tool[2] < 0.12 and np.linalg.norm(self.tool[:2] - [x,y]) > 0.04:
            return self.result("move", args, False, "lift_before_lateral_motion")
        q2 = math.acos(c)
        q1 = math.atan2(dy, dx) - math.atan2(0.30*math.sin(q2), 0.35+0.30*math.cos(q2))
        self.data.ctrl[:] = [q1, q2, z - 0.32]
        self.step(700)
        error = float(np.linalg.norm(self.tool - [x,y,z]))
        return self.result("move", args, error < 0.02, None if error < 0.02 else "tracking_error")

    def grasp(self):
        if self.holding:
            return self.result("grasp", {}, False, "already_holding")
        if np.linalg.norm(self.tool[:2] - self.block[:2]) >= 0.035 or abs(self.tool[2] - self.block[2]) >= 0.05:
            return self.result("grasp", {}, False, "not_at_block")
        if self.perturb == "miss-grasp" and not self.injected:
            self.injected = True
            return self.result("grasp", {}, False, "injected_miss_grasp")
        # Educational attachment: no finger contact/friction inference is performed.
        rotation = self.data.body("tool").xmat.reshape(3,3)
        self.model.eq_data[0,3:6] = rotation.T @ (self.block - self.tool)
        qinv = self.data.body("tool").xquat.copy()
        qinv[1:] *= -1
        qrel = np.zeros(4)
        mujoco.mju_mulQuat(qrel, qinv, self.data.body("block").xquat)
        self.model.eq_data[0,6:10] = qrel
        self.data.eq_active[0] = 1
        self.step(100)
        if self.perturb == "shift-goal" and not self.injected:
            self.injected = True
            self.data.mocap_pos[0,:2] = [0.08, 0.20]
            mujoco.mj_forward(self.model, self.data)
        return self.result("grasp", {})

    def release(self):
        if not self.holding:
            return self.result("release", {}, False, "empty_gripper")
        self.data.eq_active[0] = 0
        self.step(600)
        return self.result("release", {})

    def render(self):
        with mujoco.Renderer(self.model, height=480, width=640) as renderer:
            renderer.update_scene(self.data, camera="top")
            return renderer.render().copy()

    def locate_color(self, kind):
        if kind not in ("block", "goal"):
            return {"ok": False, "error": "unknown_kind"}
        rgb = self.render().astype(float)
        r,g,b = rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
        mask = (r > 1.8*g) & (r > 1.8*b) & (r > 80) if kind == "block" else (b > 1.5*r) & (b > 1.5*g) & (b > 80)
        yy,xx = np.nonzero(mask)
        if len(xx) < 20:
            return {"ok": False, "error": "color_not_visible", "source": "rgb_color_mask"}
        u,v = float(np.median(xx)), float(np.median(yy))
        # Fixed calibrated top camera, intersect with known horizontal top surface.
        plane_z = 0.044 if kind == "block" else 0.014
        focal = 480 / (2*math.tan(math.radians(48)/2))
        depth = 1.4 - plane_z
        xyz = [(u-319.5)*depth/focal, -(v-239.5)*depth/focal, plane_z]
        return {"ok": True, "source": "rgb_color_mask_and_calibrated_plane", "kind": kind, "pixel_uv": [u,v], "xyz": rounded(xyz), "pixels": len(xx), "assumptions": "fixed top camera; known colors; known horizontal surface heights"}

    def call(self, name, args):
        if name == "observe":
            return self.result("observe", {})
        if name not in ("move", "grasp", "release", "locate_color"):
            return {"ok":False,"error":"unknown_tool"}
        try:
            return getattr(self,name)(**args)
        except (TypeError, ValueError) as exc:
            return self.result(name,args,False,"invalid_arguments: " + str(exc))


def baseline(w):
    initial = w.observe()
    p, g = initial["scene"]["block_xyz"], initial["scene"]["goal_xyz"]
    # Deliberately ignores feedback and caches the initial goal for comparison.
    for name,args in [("move",dict(x=p[0],y=p[1],z=.18)),("move",dict(x=p[0],y=p[1],z=.06)),("grasp",{}),("move",dict(x=p[0],y=p[1],z=.18)),("move",dict(x=g[0],y=g[1],z=.18)),("move",dict(x=g[0],y=g[1],z=.065)),("release",{})]:
        w.call(name,args)


def scripted_agent(w, max_steps=32):
    # Transparent deterministic state machine: it never calls a language model.
    for _ in range(max_steps):
        obs = w.observe()
        if obs["task"]["success"]:
            return
        p,g,t = (np.array(obs["scene"]["block_xyz"]),np.array(obs["scene"]["goal_xyz"]),np.array(obs["robot"]["tool_xyz"]))
        if obs["robot"]["holding"]:
            if np.linalg.norm(t[:2]-g[:2]) > .025:
                target = [t[0],t[1],.18] if t[2] < .12 else [g[0],g[1],.18]
                w.move(*target)
            elif t[2] > .09:
                w.move(g[0],g[1],.065)
            else:
                w.release()
        elif np.linalg.norm(t[:2]-p[:2]) > .025:
            target = [t[0],t[1],.18] if t[2] < .12 else [p[0],p[1],.18]
            w.move(*target)
        elif t[2] > .085:
            w.move(p[0],p[1],.06)
        else:
            w.grasp()


def png_bytes(image):
    h,w,_ = image.shape
    raw = b"".join(b"\0"+row.tobytes() for row in image.astype(np.uint8))
    def chunk(kind, data):
        return struct.pack(">I",len(data))+kind+data+struct.pack(">I",zlib.crc32(kind+data)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")


def llm_agent(w, instruction, max_calls, out):
    endpoint, key, model = (os.getenv(x, "") for x in ("AF_BASE_URL","AF_API_KEY","AF_MODEL"))
    if not endpoint or not key or not model:
        raise ValueError("Set AF_BASE_URL, AF_API_KEY, AF_MODEL for a real model call; scripted mode needs none.")
    url = urlsplit(endpoint)
    if not url.hostname or url.query or url.fragment or (url.scheme != "https" and not (url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1", "::1"))):
        raise ValueError("Use HTTPS for a remote model endpoint, or HTTP only on loopback; omit query/fragment.")
    tooldefs = []
    for name,desc,props,required in [
        ("observe","Read simulator-state observation (privileged state teaching mode).",{},[]),
        ("move","Move world-space tool XYZ in meters; lift to z=.18 before lateral motion; z in [.045,.32].",{k:{"type":"number"} for k in ("x","y","z")},["x","y","z"]),
        ("grasp","Attach red block when close. Educational weld approximation; verify holding.",{},[]),
        ("release","Detach held block and wait for settling. Check success afterwards.",{},[])]:
        tooldefs.append({"type":"function","function":{"name":name,"description":desc,"parameters":{"type":"object","properties":props,"required":required,"additionalProperties":False}}})
    messages=[{"role":"system","content":"You operate a simplified SCARA simulator. Complete the task through tools and check outcomes. You see simulator state, not visual-only perception. Move above the block at z=.18, descend to .06, grasp, lift, move above the CURRENT blue goal, descend to .065, release. Tool success is not task success. Observe and recover from misses or a moving goal. Never claim completion unless task.success is true."},{"role":"user","content":instruction+"\n"+json.dumps(w.observe(),ensure_ascii=False)}]
    calls=0
    try:
        for _ in range(max_calls):
            payload={"model":model,"messages":messages,"tools":tooldefs,"tool_choice":"auto","max_tokens":700}
            req=urllib.request.Request(endpoint.rstrip("/")+"/chat/completions",data=json.dumps(payload).encode(),headers={"Authorization":"Bearer "+key,"Content-Type":"application/json"},method="POST")
            calls+=1
            w.model_calls = calls
            with urllib.request.urlopen(req,timeout=60) as response:
                body=json.load(response)
            msg=body["choices"][0]["message"]
            messages.append({k:v for k,v in msg.items() if k in ("role","content","tool_calls")})
            if not msg.get("tool_calls"):
                if w.success(): break
                messages.append({"role":"user","content":"Task is not complete. Current observation: "+json.dumps(w.observe())})
                continue
            for tool_index, t in enumerate(msg["tool_calls"]):
                try: args=json.loads(t["function"]["arguments"])
                except json.JSONDecodeError: args=None
                result={"ok":False,"error":"too_many_calls_in_one_response"} if tool_index >= 8 else ({"ok":False,"error":"invalid_json"} if not isinstance(args,dict) else w.call(t["function"]["name"],args))
                messages.append({"role":"tool","tool_call_id":t["id"],"content":json.dumps(result)})
            if w.success(): break
    finally:
        # Store the transcript even when a request fails; never store headers or keys.
        (out/"model-messages.json").write_text(json.dumps(messages,ensure_ascii=False,indent=2))
    return calls


def save(w, out, mode, calls=0, error=None):
    out.mkdir(parents=True,exist_ok=True)
    (out/"events.jsonl").write_text("".join(json.dumps(e,ensure_ascii=False)+"\n" for e in w.events))
    summary={"mode":mode,"seed":w.seed,"perturb":w.perturb,"success":w.success(),"steps":len(w.events),"model_calls":calls,"error":error,"observation_source":"simulator_state","grasp_model":"explicit_weld_attachment","final_observation":w.observe()}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2))
    return summary


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("command",choices=["doctor","observe","move","baseline","agent","vision","parse-goal","evaluate"])
    p.add_argument("--seed",type=int,default=7)
    p.add_argument("--out",type=Path,default=Path("runs/lab"))
    p.add_argument("--perturb",choices=["none","miss-grasp","shift-goal"],default="none")
    p.add_argument("--mode",choices=["scripted","llm"],default="scripted")
    p.add_argument("--instruction",default=DEFAULT_GOAL)
    p.add_argument("--max-calls",type=int,default=12)
    p.add_argument("--x",type=float,default=-.05);p.add_argument("--y",type=float,default=.1);p.add_argument("--z",type=float,default=.18)
    p.add_argument("--seeds",type=int,default=5)
    a=p.parse_args()
    if a.command=="parse-goal":
        print(json.dumps(parse_goal(a.instruction),ensure_ascii=False,indent=2));return
    if a.command=="doctor":
        w=World(a.seed)
        result={"python":platform.python_version(),"platform":platform.platform(),"mujoco":mujoco.__version__,"physics":"ok","grasp_model":"explicit_weld_attachment","render":"not_checked"}
        try: w.render();result["render"]="ok"
        except Exception as e: result["render"]="unavailable: "+str(e)
        print(json.dumps(result,ensure_ascii=False,indent=2));return
    if a.command=="evaluate":
        if not 1 <= a.seeds <= 100: p.error("--seeds must be 1..100")
        rows=[]
        for perturb in ("none","miss-grasp","shift-goal"):
            for mode in ("baseline","scripted"):
                for seed in range(a.seeds):
                    w=World(seed,perturb)
                    (baseline if mode=="baseline" else scripted_agent)(w)
                    rows.append(save(w,a.out/f"{perturb}-{mode}-{seed}",mode))
        a.out.mkdir(parents=True,exist_ok=True)
        (a.out/"evaluation.json").write_text(json.dumps(rows,ensure_ascii=False,indent=2))
        aggregate=[{"perturb":s,"mode":m,"successes":sum(r["success"] for r in rows if r["perturb"]==s and r["mode"]==m),"episodes":a.seeds} for s in ("none","miss-grasp","shift-goal") for m in ("baseline","scripted")]
        print(json.dumps(aggregate,indent=2));return
    w=World(a.seed,a.perturb);a.out.mkdir(parents=True,exist_ok=True)
    if a.command=="observe": print(json.dumps(w.observe(),indent=2));return
    if a.command=="move":
        result=w.move(a.x,a.y,a.z);print(json.dumps(result,indent=2));save(w,a.out,"manual_move");sys.exit(0 if result["ok"] else 2)
    if a.command=="vision":
        image=w.render();(a.out/"top-camera.png").write_bytes(png_bytes(image))
        result={"block":w.locate_color("block"),"goal":w.locate_color("goal"),"scope":"controlled color localization exercise, not a VLM or visual action loop"}
        (a.out/"vision.json").write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False,indent=2));return
    calls,error=0,None
    if a.command=="baseline": baseline(w);mode="baseline"
    else:
        goal=parse_goal(a.instruction)
        if goal["status"]!="ready": print(json.dumps(goal,ensure_ascii=False,indent=2));sys.exit(2)
        mode=a.mode
        if mode=="scripted": scripted_agent(w)
        else:
            if not 1 <= a.max_calls <= 50: p.error("--max-calls must be 1..50")
            try: calls=llm_agent(w,a.instruction,a.max_calls,a.out)
            except Exception as e:
                calls=w.model_calls
                error=type(e).__name__+": "+str(e)
    summary=save(w,a.out,mode,calls,error);print(json.dumps(summary,ensure_ascii=False,indent=2))
    sys.exit(0 if summary["success"] else 2)

if __name__=="__main__": main()
