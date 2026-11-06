"""Physical outcomes, causal comparisons, and program/memory boundaries."""
import json
from pathlib import Path
import tempfile
import unittest

import mujoco
import numpy as np
from advanced import (BASE, World, TaskMemory, SpatialMemory, execute_program,
                      memory_experiment, spatial_experiment, learned_skill_experiment,
                      benchmark_experiment, capstone_experiment)
from run import scripted_agent


class AdvancedTests(unittest.TestCase):
    def test_completion_record_requires_current_evidence(self):
        w, memory = World(), TaskMemory()
        self.assertFalse(memory.remember("red_to_blue", w))
        scripted_agent(w)
        self.assertTrue(memory.remember("red_to_blue", w))
        self.assertTrue(memory.skip_completed("red_to_blue", w))
        w.data.mocap_pos[0, :2] = [.08, .20]
        mujoco.mj_forward(w.model, w.data)
        self.assertFalse(memory.skip_completed("red_to_blue", w))
        self.assertNotIn("red_to_blue", memory.completed)

    def test_memory_experiment_keeps_evidence(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            summary = memory_experiment(7, out)
            self.assertTrue(summary["success"])
            self.assertEqual(summary["skipped_duplicates"], 1)
            record = json.loads((out / "memory.json").read_text())
            self.assertTrue(record["completed"]["red_to_blue"]["observation"]["task"]["success"])

    def test_spatial_expiry_and_change(self):
        memory = SpatialMemory()
        memory.observe([0, 0, 0], 0)
        self.assertIsNotNone(memory.lookup(1))
        self.assertIsNone(memory.lookup(3))
        memory.observe([.1, 0, 0], 3)
        self.assertFalse(memory.records[0]["valid"])
        self.assertEqual(memory.records[-1]["update_reason"], "position_changed")
        with tempfile.TemporaryDirectory() as d:
            cases = spatial_experiment(7, Path(d))["cases"]
            self.assertEqual([c["success"] for c in cases], [False, True])

    def test_program_validates_all_nodes_before_motion(self):
        bad_nodes = [{"call": "__import__", "args": {}}, {"call": []},
                     {"if": {}, "then": []}, {"repeat": 1000000, "steps": []},
                     {"call": "move", "args": {"x": "block.__class__", "y": 0, "z": .18}}]
        for node in bad_nodes:
            w = World()
            before = w.data.qpos.copy()
            doc = {"version": 1, "steps": [{"call": "move", "args": {"x": -.1, "y": .1, "z": .18}}, node]}
            with self.assertRaises(ValueError):
                execute_program(w, doc)
            np.testing.assert_array_equal(before, w.data.qpos)
            self.assertFalse(w.events)

    def test_program_budget_and_recovery(self):
        doc = json.loads((BASE / "example-program.json").read_text())
        w = World(7, "miss-grasp")
        result = execute_program(w, doc, 2)
        self.assertEqual(result["error"], "program_budget_exhausted")
        self.assertEqual(result["executed_nodes"], 2)
        self.assertEqual(len(w.events), 2)
        for perturb in ("none", "miss-grasp", "shift-goal"):
            with self.subTest(perturb=perturb):
                w = World(7, perturb)
                self.assertTrue(execute_program(w, doc, 64)["success"])

    def test_learning_fits_data_but_does_not_fake_ood_success(self):
        with tempfile.TemporaryDirectory() as d:
            result = learned_skill_experiment(7, Path(d))
            groups = {(g["split"], g["policy"]): g for g in result["groups"]}
            self.assertEqual(groups[("id", "learned")]["successes"], 20)
            self.assertLess(groups[("ood", "learned")]["successes"], 20)
            self.assertEqual(groups[("ood", "analytic")]["successes"], 20)
            weights = json.loads((Path(d) / "weights.json").read_text())
            self.assertEqual(np.array(weights["weights"]).shape, (6, 2))

    def test_benchmark_matches_conditions(self):
        with tempfile.TemporaryDirectory() as d:
            result = benchmark_experiment(2, Path(d))
            self.assertEqual(result["episodes"], 24)
            rows = json.loads((Path(d) / "episodes.json").read_text())
            for seed in (0, 1):
                for perturb in ("none", "miss-grasp", "shift-goal"):
                    group = [r for r in rows if r["seed"] == seed and r["perturb"] == perturb]
                    self.assertEqual(len(group), 4)
                    for row in group:
                        self.assertEqual(row["initial_observation"], group[0]["initial_observation"])
            groups = {(g["perturb"], g["policy"]): g for g in result["groups"]}
            self.assertEqual(groups[("miss-grasp", "no-retry")]["successes"], 0)
            self.assertEqual(groups[("shift-goal", "stale-spatial")]["successes"], 0)

    def test_two_real_bodies_recover_without_losing_first_goal(self):
        for seed in (0, 7, 19):
            for perturb in ("none", "miss-grasp", "shift-goal"):
                with self.subTest(seed=seed, perturb=perturb), tempfile.TemporaryDirectory() as d:
                    result = capstone_experiment(seed, Path(d), perturb)
                    self.assertTrue(result["success"])
                    self.assertEqual(len(result["completed_ids"]), 2)
                    self.assertEqual(result["skipped_duplicates"], 1)
                    for obj in result["final_observation"]["objects"].values():
                        self.assertFalse(obj["holding"])
                        self.assertLess(np.linalg.norm(np.array(obj["block_xyz"][:2])-obj["goal_xyz"][:2]), .045)
                        self.assertLess(obj["linear_speed_m_s"], .05)
                    events = (Path(d) / "events.jsonl").read_text()
                    if perturb == "miss-grasp":
                        self.assertIn("injected_miss_grasp", events)


if __name__ == "__main__":
    unittest.main()
