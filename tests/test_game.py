import math
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from main import (App, World, FPS, FIELD_TOP, FIELD_BOTTOM, W, LENGTH,
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

    def test_movement_stop_freezes_current_angle_immediately(self):
        g = self.clean(True)
        g.step(1, 0)
        self.assertGreater(abs(g.omega), 0)
        angle = g.angle
        self.assertGreater(abs(wrap(g.angle-g.target_angle)), .1)
        g.step()
        self.assertEqual(g.angle, angle)
        self.assertEqual(g.omega, 0)
        for _ in range(60):
            g.step()
        self.assertEqual(g.angle, angle)

    def test_mouse_pointer_position_following(self):
        g = self.clean(True)
        g.step(pointer=(160, 170))
        self.assertEqual((g.x, g.y), (160, 170))
        angle = g.angle
        g.step(pointer=(160, 170))
        self.assertEqual(g.angle, angle)
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


class InputTests(unittest.TestCase):
    def app(self, touch=True):
        from types import SimpleNamespace
        app = App.__new__(App)
        keys = ['MOUSE_BUTTON_LEFT','KEY_M','KEY_RETURN','KEY_T','KEY_ESCAPE','KEY_P',
                'KEY_R','KEY_RIGHT','KEY_D','KEY_LEFT','KEY_A','KEY_DOWN','KEY_S','KEY_UP','KEY_W']
        app.p = SimpleNamespace(**{key:key for key in keys}, mouse_x=48, mouse_y=342)
        app.held = app.tap = False
        app.p.btnp = lambda key: key=='MOUSE_BUTTON_LEFT' and app.tap
        app.p.btn = lambda key: key=='MOUSE_BUTTON_LEFT' and app.held
        app.web = SimpleNamespace(swingTouch=touch, swingBlurCount=0)
        app.blur_seen=0
        app.screen='game'
        app.pause=app.input_lock=app.stick_active=app.sound=False
        app.stick_vector=(0.,0.)
        app.last_pointer=(48,342)
        app.world=World(True,seed=1)
        return app

    def test_stick_release_and_centre_stop_player_and_blade(self):
        app=self.app()
        app.p.mouse_x=72
        app.tap=app.held=True
        x=app.world.x
        app.update()
        self.assertGreater(app.world.x,x)
        app.tap=False
        app.p.mouse_x=48
        x,angle=app.world.x,app.world.angle
        app.update()
        self.assertEqual((app.world.x,app.world.angle),(x,angle))
        app.p.mouse_x=72
        app.update()
        app.held=False
        x,angle=app.world.x,app.world.angle
        app.update()
        self.assertEqual((app.world.x,app.world.angle),(x,angle))
        self.assertEqual(app.world.omega,0)

    def test_battlefield_touch_does_not_teleport_player(self):
        app=self.app()
        app.p.mouse_x,app.p.mouse_y=180,160
        app.tap=app.held=True
        xy=(app.world.x,app.world.y)
        app.update()
        self.assertEqual((app.world.x,app.world.y),xy)

    def test_mouse_tracks_pointer_and_blur_cancels_stick(self):
        app=self.app(False)
        app.p.mouse_x,app.p.mouse_y=160,190
        app.update()
        self.assertEqual((app.world.x,app.world.y),(160,190))
        app.stick_active=True
        app.web.swingBlurCount=1
        xy=(app.world.x,app.world.y)
        app.update()
        self.assertTrue(app.pause)
        self.assertFalse(app.stick_active)
        self.assertEqual((app.world.x,app.world.y),xy)


if __name__ == '__main__':
    unittest.main()
