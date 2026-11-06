"""Regression checks for physical outcomes and teaching-mode boundaries."""
import tempfile
import unittest
import io
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from run import World, baseline, scripted_agent, parse_goal, save, llm_agent


class LabTests(unittest.TestCase):
    def test_no_disturbance_and_recovery(self):
        for seed in (0, 7, 19):
            for perturb in ("none", "miss-grasp", "shift-goal"):
                with self.subTest(seed=seed, perturb=perturb):
                    w = World(seed, perturb)
                    baseline(w)
                    self.assertEqual(w.success(), perturb == "none")
                    w = World(seed, perturb)
                    scripted_agent(w)
                    self.assertTrue(w.success())
                    self.assertFalse(w.holding)
                    self.assertLess(np.linalg.norm(w.block[:2] - w.goal[:2]), .045)

    def test_invalid_motion_does_not_mutate_state(self):
        w = World()
        before = w.data.qpos.copy()
        for xyz in ((5, 5, .18), (0, 0, -1), (float("nan"), 0, .1)):
            self.assertFalse(w.move(*xyz)["ok"])
            np.testing.assert_array_equal(before, w.data.qpos)

    def test_empty_and_distant_gripper(self):
        w = World()
        self.assertEqual(w.grasp()["error"], "not_at_block")
        self.assertEqual(w.release()["error"], "empty_gripper")
        self.assertFalse(w.holding)

    def test_language_scope_and_negation(self):
        self.assertEqual(parse_goal("请把红色方块放到蓝色区域。 ")["status"], "ready")
        self.assertEqual(parse_goal("Put the red block in the blue area.")["status"], "ready")
        for instruction in ("不要把红色方块放到蓝色区域", "把红色方块放到蓝色区域，然后跳舞", "整理桌面", "把绿色方块放到蓝色区域"):
            self.assertEqual(parse_goal(instruction)["status"], "needs_clarification")

    def test_mode_and_log_provenance(self):
        w = World(7, "miss-grasp")
        scripted_agent(w)
        with tempfile.TemporaryDirectory() as d:
            summary = save(w, Path(d), "scripted")
            self.assertEqual(summary["model_calls"], 0)
            self.assertEqual(summary["grasp_model"], "explicit_weld_attachment")
            self.assertIn("injected_miss_grasp", (Path(d)/"events.jsonl").read_text())

    def test_model_budget_and_failure_transcript(self):
        # A protocol mock checks our adapter, not any real provider/model ability.
        env = {"AF_BASE_URL": "https://example.invalid/v1", "AF_API_KEY": "test-only-not-a-real-key", "AF_MODEL": "protocol-test"}
        response = {"choices": [{"message": {"role": "assistant", "content": "not complete"}}]}
        def reply(*args, **kwargs):
            return io.BytesIO(json.dumps(response).encode())
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", env):
            w = World()
            with patch("urllib.request.urlopen", side_effect=reply) as request:
                self.assertEqual(llm_agent(w, "test", 2, Path(d)), 2)
                self.assertEqual(request.call_count, 2)
            self.assertFalse(w.success())
            self.assertNotIn(env["AF_API_KEY"], (Path(d)/"model-messages.json").read_text())
            w = World()
            with patch("urllib.request.urlopen", side_effect=OSError("test disconnect")):
                with self.assertRaises(OSError):
                    llm_agent(w, "test", 2, Path(d))
            self.assertEqual(w.model_calls, 1)
            self.assertTrue(json.loads((Path(d)/"model-messages.json").read_text()))

    def test_remote_plain_http_is_rejected(self):
        with tempfile.TemporaryDirectory() as d, patch.dict("os.environ", {"AF_BASE_URL": "http://localhost.example.invalid/v1", "AF_API_KEY": "test", "AF_MODEL": "test"}):
            w = World()
            with patch("urllib.request.urlopen") as request:
                with self.assertRaises(ValueError):
                    llm_agent(w, "test", 1, Path(d))
                request.assert_not_called()


if __name__ == "__main__":
    unittest.main()
