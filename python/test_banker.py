"""Run: python test_banker.py   (or: python -m pytest test_banker.py)"""
import unittest

import banker
from samples import SAMPLES
from script import build_script


class TestSamples(unittest.TestCase):
    def test_samples_match_hand_answers(self):
        for s in SAMPLES:
            with self.subTest(sample=s["name"]):
                self.assertEqual(banker.validate_state(s["state"]), [])
                r = banker.safety(s["state"])
                self.assertEqual(r["safe"], s["expected"]["safe"])
                self.assertEqual(r["sequence"], s["expected"]["sequence"])
                q = banker.request(s["state"], s["request"]["pid"], s["request"]["req"])
                self.assertEqual(q["status"], s["expected"]["status"])
                self.assertEqual(q["code"], s["expected"]["code"])

    def test_need(self):
        self.assertEqual(banker.compute_need(SAMPLES[0]["state"]),
                         [[7, 4, 3], [1, 2, 2], [6, 0, 0], [0, 1, 1], [4, 3, 1]])

    def test_unsafe_request_does_not_touch_state(self):
        s = SAMPLES[1]["state"]
        r = banker.request(s, 0, [0, 2, 0])
        self.assertIs(r["new_state"], s)
        self.assertEqual(s["available"], [2, 3, 0])

    def test_validation(self):
        bad = {"available": [1, -1], "max": [[1, 1]], "alloc": [[2, 0]]}
        self.assertEqual(len(banker.validate_state(bad)), 2)

    def test_every_sample_builds_a_script(self):
        for s in SAMPLES:
            beats = build_script(s)
            self.assertGreater(len(beats), 5)
            self.assertTrue(all(b.caption for b in beats))


if __name__ == "__main__":
    unittest.main()
