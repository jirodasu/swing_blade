import math
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import World, LENGTH, ROUND_FRAMES, segment_distance


class GameTests(unittest.TestCase):
    def test_reversal_makes_faster_swing_than_straight_travel(self):
        g = World(practice=True, seed=1)
        for _ in range(160):
            g.step(1, 0)
        straight = abs(g.omega)
        peak = 0
        for _ in range(30):
            g.step(-1, 0)
            peak = max(peak, abs(g.omega))
        self.assertGreater(peak, straight + .05)

    def test_stationary_blade_does_not_auto_kill(self):
        g = World(practice=True, seed=2)
        g.enemies = [dict(x=g.x, y=g.y+25, hp=1, r=5, speed=0, cool=0, kind=0)]
        for _ in range(90):
            g.step(0, 0)
        self.assertEqual(g.kills, 0)
        self.assertEqual(g.hp, 5)

    def test_fast_blade_hits_target(self):
        g = World(seed=1)
        g.angle = 0
        g.omega = .25
        g.enemies = [dict(x=g.x+25, y=g.y+3, hp=1, r=5, speed=0, cool=0, kind=0)]
        g.step(0, 0)
        self.assertEqual(g.kills, 1)
        self.assertIn('hit', g.events)

    def test_damage_has_grace_period(self):
        g = World(seed=1)
        g.enemies = [dict(x=g.x, y=g.y, hp=99, r=5, speed=0, cool=0, kind=0)]
        for _ in range(40):
            g.step(0, 0)
        self.assertEqual(g.hp, 4)

    def test_timer_stops_at_win(self):
        g = World(seed=1)
        g.age = ROUND_FRAMES-1
        g.step(0, 0)
        self.assertEqual(g.state, 'win')
        for _ in range(10):
            g.step(1, 0)
        self.assertEqual(g.age, ROUND_FRAMES)

    def test_long_session_is_bounded_and_finite(self):
        g = World(practice=True, seed=42)
        for frame in range(36000):
            g.step(math.cos(frame*.047), math.sin(frame*.047))
            self.assertTrue(10 <= g.x <= 170 and 54 <= g.y <= 250)
            self.assertTrue(math.isfinite(g.angle))
            self.assertLessEqual(abs(g.omega), .3)
        self.assertEqual(g.state, 'play')
        self.assertEqual(g.hp, 5)

    def test_segment_distance_clamps_to_endpoints(self):
        self.assertAlmostEqual(segment_distance(15, 0, 0, 0, 10, 0), 5)
        self.assertAlmostEqual(segment_distance(5, 3, 0, 0, 10, 0), 3)


if __name__ == '__main__':
    unittest.main()
