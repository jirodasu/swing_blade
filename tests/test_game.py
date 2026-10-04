import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import (World, FPS, FIELD_TOP, FIELD_BOTTOM, W, LENGTH,
                  LEVEL_FRAMES, MULTIPLIER_GRACE, MULTIPLIER_DECAY,
                  ENEMY_SCORE, GEM_SCORE, segment_distance, wrap)


def bullet(x, y, vx=0., vy=0.):
    return dict(x=x, y=y, vx=vx, vy=vy, r=3, scored=False)


def enemy(x, y):
    return dict(x=x, y=y, r=6, vx=0., vy=0., fire=999999, kind=0)


class GameTests(unittest.TestCase):
    def clean(self, practice=False):
        g = World(practice, seed=1)
        g.enemies = []
        g.spawn_wait = 100000
        return g

    def test_reversal_swings_to_opposite_direction_and_stops(self):
        g = self.clean(True)
        g.step(pointer=(150, 185))
        for _ in range(90):
            g.step()
        self.assertLess(abs(wrap(g.angle-math.pi)), .02)
        self.assertEqual(g.omega, 0)
        g.step(pointer=(120, 185))
        self.assertGreater(abs(g.omega), .1)
        for _ in range(90):
            g.step()
        self.assertLess(abs(wrap(g.angle)), .02)
        self.assertEqual(g.omega, 0)

    def test_blade_contact_boosts_but_does_not_destroy_bullet(self):
        g = self.clean()
        b = bullet(g.x, g.y-25)
        g.bullets = [b]
        g.step()
        self.assertEqual(len(g.bullets), 1)
        self.assertEqual(g.multiplier, 2)
        self.assertEqual(g.state, 'play')
        for _ in range(20):
            g.step()
        self.assertEqual(g.bullet_hits, 1)

    def test_bullet_hit_is_fatal_and_game_stops(self):
        g = self.clean()
        g.bullets = [bullet(g.x, g.y)]
        g.step()
        self.assertEqual(g.state, 'lose')
        age = g.age
        g.step(1, 0)
        self.assertEqual(g.age, age)

    def test_visible_ship_edge_is_not_hitbox(self):
        g = self.clean()
        g.bullets = [bullet(g.x+6, g.y)]
        g.step()
        self.assertEqual(g.state, 'play')

    def test_pointer_jump_cannot_skip_a_bullet(self):
        g = self.clean()
        g.bullets = [bullet(g.x+15, g.y)]
        g.step(pointer=(g.x+30, g.y))
        self.assertEqual(g.state, 'lose')

    def test_enemy_cut_drops_gem_and_scores_at_multiplier(self):
        g = self.clean()
        g.multiplier = 4
        g.enemies = [enemy(g.x, g.y-25)]
        g.step()
        self.assertEqual(g.kills, 1)
        self.assertEqual(g.score, ENEMY_SCORE*4)
        self.assertEqual(len(g.gems), 1)
        gem = g.gems[0]
        g.step(pointer=(gem['x'], gem['y']))
        self.assertEqual(g.gems_collected, 1)
        self.assertEqual(g.score, (ENEMY_SCORE+GEM_SCORE)*4)
        self.assertEqual(g.gems, [])

    def test_idle_multiplier_decays_to_one(self):
        g = self.clean()
        g.multiplier = 3
        for _ in range(MULTIPLIER_GRACE+MULTIPLIER_DECAY):
            g.step()
        self.assertEqual(g.multiplier, 1)
        for _ in range(60):
            g.step()
        self.assertEqual(g.multiplier, 1)

    def test_practice_bullets_cannot_kill(self):
        g = self.clean(True)
        g.bullets = [bullet(g.x, g.y)]
        g.step()
        self.assertEqual(g.state, 'play')

    def test_endless_round_and_level_escalation(self):
        g = self.clean()
        g.age = 30*FPS-1
        g.step()
        self.assertEqual(g.state, 'play')
        self.assertEqual(g.level, 3)
        g.age = LEVEL_FRAMES-1
        g.step()
        self.assertEqual(g.level, 2)
        low = enemy(20, 60)
        g.fire(low)
        speed2 = math.hypot(g.bullets[-1]['vx'], g.bullets[-1]['vy'])
        g.age = 5*LEVEL_FRAMES
        g.fire(low)
        self.assertGreater(math.hypot(g.bullets[-1]['vx'], g.bullets[-1]['vy']), speed2)

    def test_fast_pointer_motion_sweeps_blade(self):
        g = self.clean()
        g.angle = g.target_angle = 0
        g.enemies = [enemy(g.x+10, g.y+40)]
        g.step(pointer=(g.x, g.y+80))
        self.assertEqual(g.kills, 1)

    def test_long_training_session_stays_bounded(self):
        g = World(True, seed=42)
        for frame in range(18000):
            g.step(math.cos(frame*.047), math.sin(frame*.047))
            self.assertTrue(4 <= g.x <= W-4)
            self.assertTrue(FIELD_TOP+4 <= g.y <= FIELD_BOTTOM-4)
            self.assertTrue(math.isfinite(g.angle))
            self.assertLessEqual(len(g.bullets), 12)
            self.assertLessEqual(len(g.gems), 100)
        self.assertEqual(g.state, 'play')

    def test_segment_distance_clamps_to_endpoints(self):
        self.assertAlmostEqual(segment_distance(15, 0, 0, 0, 10, 0), 5)
        self.assertAlmostEqual(segment_distance(5, 3, 0, 0, 10, 0), 3)


if __name__ == '__main__':
    unittest.main()
