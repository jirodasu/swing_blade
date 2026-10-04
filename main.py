# title: SWING BLADE - bullet scoring prototype
# author: jirodasu
# version: 0.2.1
"""Video-observed Zanki rules; unknown numeric values are prototype tuning."""
import math
import random

W, H, FPS = 240, 400, 60
STICK_X, STICK_Y, STICK_RADIUS, STICK_DEADZONE = 48, 342, 32, 5
FIELD_TOP, FIELD_BOTTOM = 40, 280
LENGTH = 43
MOVE_SPEED = 2.4
ANGULAR_DAMPING = .50
ANGLE_SPRING = .72
ANGLE_SNAP = .012
MAX_OMEGA = .48
BLADE_WIDTH = 3
HIT_RADIUS = .5  # One pixel at the centre, not the ship sprite.
LEVEL_FRAMES = 15 * FPS
MULTIPLIER_GRACE = 60
MULTIPLIER_DECAY = 18
ENEMY_SCORE, GEM_SCORE = 100, 200


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def segment_distance(x, y, ax, ay, bx, by):
    dx, dy = bx-ax, by-ay
    t = clamp(((x-ax)*dx+(y-ay)*dy) / max(dx*dx+dy*dy, .0001), 0, 1)
    return math.hypot(x-ax-t*dx, y-ay-t*dy)


class World:
    def __init__(self, practice=False, seed=None):
        self.rng = random.Random(seed)
        self.practice = practice
        self.x, self.y = W/2, 185.
        self.angle = -math.pi/2
        self.target_angle = self.angle
        self.omega = 0.
        self.age = self.kills = self.score = self.gems_collected = 0
        self.multiplier = 1
        self.combo_idle = self.bullet_hits = 0
        self.state = 'play'
        self.enemies, self.bullets, self.gems = [], [], []
        self.particles, self.trail, self.labels, self.events = [], [], [], []
        self.spawn_wait = 90
        if practice:
            self.practice_targets()

    @property
    def level(self):
        return 1+self.age//LEVEL_FRAMES

    def practice_targets(self):
        self.enemies = [dict(x=175., y=120., r=6, vx=0., vy=0., fire=999999, kind=0)]

    def spawn(self):
        # These patterns are approximations, not recovered original source values.
        side = self.rng.randrange(3)
        if side == 0:
            x, y, vx, vy = self.rng.uniform(20, W-20), FIELD_TOP-8., 0., .45
        else:
            x, y = (-8. if side == 1 else W+8.), self.rng.uniform(60, 150)
            vx, vy = (.4 if side == 1 else -.4), .18
        kind = self.rng.randrange(min(3, self.level))
        self.enemies.append(dict(x=x, y=y, r=6, vx=vx, vy=vy,
                                 fire=45, kind=kind))

    def fire(self, e):
        a = math.atan2(self.y-e['y'], self.x-e['x'])
        speed = min(2.1, .8+(self.level-1)*.12)
        offsets = [0] if e['kind'] == 0 else ([-.26, 0, .26] if e['kind'] == 1 else [-.5, -.25, 0, .25, .5])
        for offset in offsets:
            if len(self.bullets) >= 260:
                break
            self.bullets.append(dict(x=e['x'], y=e['y'], vx=math.cos(a+offset)*speed,
                                     vy=math.sin(a+offset)*speed, r=3, scored=False))

    def burst(self, x, y, color, count=9):
        for _ in range(count):
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(.4, 2.)
            self.particles.append([x, y, math.cos(a)*s, math.sin(a)*s, 18, color])

    def boost(self, x, y):
        self.multiplier += 1
        self.bullet_hits += 1
        self.combo_idle = 0
        self.labels.append([x, y, '+1', 30, 12])
        self.events.append('boost')

    def blade_hit(self, x, y, radius, ox, oy, oa):
        # Interpolate both angle and pivot. Also handles large pointer jumps.
        da = wrap(self.angle-oa)
        steps = max(1, math.ceil((math.hypot(self.x-ox, self.y-oy)+abs(da)*LENGTH)/2))
        for k in range(steps+1):
            t = k/steps
            a = oa+da*t
            px, py = ox+(self.x-ox)*t, oy+(self.y-oy)*t
            ca, sa = math.cos(a), math.sin(a)
            if segment_distance(x, y, px+ca*8, py+sa*8,
                                px+ca*LENGTH, py+sa*LENGTH) <= radius+BLADE_WIDTH:
                return True
        return False

    def step(self, ux=0., uy=0., pointer=None):
        self.events = []
        if self.state != 'play':
            return
        self.age += 1
        self.combo_idle += 1
        if self.combo_idle >= MULTIPLIER_GRACE and (self.combo_idle-MULTIPLIER_GRACE) % MULTIPLIER_DECAY == 0:
            self.multiplier = max(1, self.multiplier-1)
        ox, oy, oa = self.x, self.y, self.angle
        if pointer is not None:
            self.x = clamp(pointer[0], 4, W-4)
            self.y = clamp(pointer[1], FIELD_TOP+4, FIELD_BOTTOM-4)
        else:
            n = max(1., math.hypot(ux, uy))
            self.x = clamp(self.x+ux/n*MOVE_SPEED, 4, W-4)
            self.y = clamp(self.y+uy/n*MOVE_SPEED, FIELD_TOP+4, FIELD_BOTTOM-4)
        dx, dy = self.x-ox, self.y-oy
        if math.hypot(dx, dy) <= .05:
            self.omega = 0.
            self.target_angle = self.angle
        else:
            self.target_angle = math.atan2(-dy, -dx)
            error = wrap(self.target_angle-self.angle)
            # Move toward the opposite-travel direction without continuing whole turns.
            self.omega = clamp((self.omega+error*ANGLE_SPRING)*ANGULAR_DAMPING, -MAX_OMEGA, MAX_OMEGA)
            if abs(error) < ANGLE_SNAP and abs(self.omega) < ANGLE_SNAP:
                self.angle, self.omega = self.target_angle, 0.
            else:
                advance = self.omega
                if advance*error > 0 and abs(advance) >= abs(error):
                    self.angle, self.omega = self.target_angle, 0.
                else:
                    self.angle = wrap(self.angle+advance)
        self.trail.append((self.x, self.y, self.angle))
        self.trail = self.trail[-6:]
        if not self.practice:
            self.spawn_wait -= 1
            if self.spawn_wait <= 0:
                if len(self.enemies) < 32:
                    self.spawn()
                self.spawn_wait = max(25, 85-(self.level-1)*8)
        surviving = []
        for e in self.enemies:
            e['x'] += e['vx']
            e['y'] += e['vy']
            if self.blade_hit(e['x'], e['y'], e['r'], ox, oy, oa):
                self.kills += 1
                self.score += ENEMY_SCORE*self.multiplier
                self.events.append('hit')
                self.burst(e['x'], e['y'], 9)
                self.labels.append([e['x'], e['y'], str(ENEMY_SCORE*self.multiplier), 30, 9])
                if len(self.gems) < 100:
                    self.gems.append(dict(x=e['x'], y=e['y'], life=8*FPS))
            elif -20 <= e['x'] <= W+20 and e['y'] <= FIELD_BOTTOM+20:
                if not self.practice:
                    e['fire'] -= 1
                    if e['fire'] <= 0:
                        self.fire(e)
                        e['fire'] = max(35, 120-(self.level-1)*8)
                surviving.append(e)
        self.enemies = surviving
        # Training also includes nonlethal bullets to learn multiplier scoring.
        if self.practice and not self.bullets:
            self.bullets.append(dict(x=8., y=155., vx=.7, vy=0., r=3, scored=False))
        live_bullets = []
        for b in self.bullets:
            bx, by = b['x'], b['y']
            b['x'] += b['vx']
            b['y'] += b['vy']
            if not b['scored'] and self.blade_hit(b['x'], b['y'], b['r'], ox, oy, oa):
                b['scored'] = True
                self.boost(b['x'], b['y'])
            # Relative swept collision: pointer movement cannot teleport through bullets.
            if not self.practice and segment_distance(0, 0, bx-ox, by-oy,
                    b['x']-self.x, b['y']-self.y) <= b['r']+HIT_RADIUS:
                self.state = 'lose'
            if -12 <= b['x'] <= W+12 and FIELD_TOP-12 <= b['y'] <= FIELD_BOTTOM+12:
                live_bullets.append(b)
        self.bullets = live_bullets
        if self.state == 'lose':
            self.events.append('hurt')
            self.burst(self.x, self.y, 8, 20)
        else:
            remaining = []
            for gem in self.gems:
                gem['life'] -= 1
                if segment_distance(gem['x'], gem['y'], ox, oy, self.x, self.y) <= 7:
                    points = GEM_SCORE*self.multiplier
                    self.score += points
                    self.gems_collected += 1
                    self.events.append('gem')
                    self.labels.append([gem['x'], gem['y'], str(points), 30, 11])
                elif gem['life'] > 0:
                    remaining.append(gem)
            self.gems = remaining
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        for label in self.labels:
            label[1] -= .3
            label[3] -= 1
        self.labels = self.labels[-50:]
        self.labels = [label for label in self.labels if label[3] > 0]
        if self.practice and not self.enemies:
            self.practice_targets()


class App:
    def __init__(self):
        import pyxel
        self.p = pyxel
        pyxel.init(W, H, title='SWING BLADE / jirodasu', fps=FPS, quit_key=pyxel.KEY_NONE)
        for i, c in {1:0x183340, 5:0x748D99, 6:0xA8CADB, 7:0xF1F4EF,
                     11:0x41C99C, 12:0x3198CD, 13:0xDCE3DF}.items():
            pyxel.colors[i] = c
        pyxel.mouse(True)
        pyxel.sounds[0].set('c3g3c4', 'n', '653', 'f', 3)
        pyxel.sounds[1].set('c2a1', 'p', '65', 'f', 6)
        pyxel.sounds[2].set('c4e4g4', 't', '543', 'n', 3)
        pyxel.sounds[3].set('e4g4', 't', '43', 'n', 3)
        self.sound = True
        self.screen = 'title'
        self.world = World(True)
        self.pause = False
        self.input_lock = False
        self.last_pointer = (pyxel.mouse_x, pyxel.mouse_y)
        self.stick_active = False
        self.stick_vector = (0., 0.)
        self.web = None
        self.blur_seen = 0
        try:
            from js import window
            self.web = window
        except ImportError:
            pass
        pyxel.run(self.update, self.draw)

    def start(self, practice):
        self.world = World(practice)
        self.screen = 'game'
        self.pause = False
        self.input_lock = True
        self.last_pointer = (self.p.mouse_x, self.p.mouse_y)
        self.stick_active = False
        self.stick_vector = (0., 0.)

    def update(self):
        p = self.p
        if self.web is not None and int(self.web.swingBlurCount) != self.blur_seen:
            self.blur_seen = int(self.web.swingBlurCount)
            self.input_lock = True
            self.stick_active = False
            self.stick_vector = (0., 0.)
            if self.screen == 'game' and self.world.state == 'play':
                self.pause = True
        tap = p.btnp(p.MOUSE_BUTTON_LEFT)
        mx, my = p.mouse_x, p.mouse_y
        if p.btnp(p.KEY_M) or (tap and mx > W-38 and my < 35):
            self.sound = not self.sound
        if self.screen == 'title':
            if p.btnp(p.KEY_RETURN) or (tap and 190 <= my <= 218):
                self.start(False)
            elif p.btnp(p.KEY_T) or (tap and 232 <= my <= 260):
                self.start(True)
            return
        if self.world.state != 'play':
            if p.btnp(p.KEY_RETURN) or (tap and 190 <= my <= 218):
                self.start(self.world.practice)
            elif p.btnp(p.KEY_ESCAPE) or (tap and 232 <= my <= 260):
                self.screen = 'title'
            return
        if p.btnp(p.KEY_ESCAPE) or (tap and 35 <= mx < 70 and my < 35):
            self.screen = 'title'
            return
        if p.btnp(p.KEY_P) or (tap and mx < 32 and my < 35):
            self.pause = not self.pause
            self.input_lock = True
        if self.pause:
            self.stick_active = False
            self.stick_vector = (0., 0.)
            self.last_pointer = (mx, my)
            return
        if self.input_lock:
            self.last_pointer = (mx, my)
            if p.btn(p.MOUSE_BUTTON_LEFT):
                return
            self.input_lock = False
        ux = int(p.btn(p.KEY_RIGHT) or p.btn(p.KEY_D))-int(p.btn(p.KEY_LEFT) or p.btn(p.KEY_A))
        uy = int(p.btn(p.KEY_DOWN) or p.btn(p.KEY_S))-int(p.btn(p.KEY_UP) or p.btn(p.KEY_W))
        if self.world.practice and (p.btnp(p.KEY_R) or (tap and 140 <= mx < 226 and 316 <= my < 352)):
            self.start(True)
            return
        pointer = None
        touch = self.web is not None and bool(self.web.swingTouch)
        moved = (mx, my) != self.last_pointer
        if tap and math.hypot(mx-STICK_X, my-STICK_Y) <= STICK_RADIUS+10:
            self.stick_active = True
        if not p.btn(p.MOUSE_BUTTON_LEFT):
            self.stick_active = False
        self.stick_vector = (0., 0.)
        if self.stick_active:
            dx, dy = mx-STICK_X, my-STICK_Y
            d = math.hypot(dx, dy)
            if d > STICK_DEADZONE:
                strength = min(1., (d-STICK_DEADZONE)/(STICK_RADIUS-STICK_DEADZONE))
                ux, uy = dx/d*strength, dy/d*strength
                self.stick_vector = (ux, uy)
            else:
                ux = uy = 0.
        elif not touch and not (ux or uy) and moved and FIELD_TOP <= my < FIELD_BOTTOM and 0 <= mx < W:
            pointer = (mx, my)
        self.last_pointer = (mx, my)
        self.world.step(ux, uy, pointer)
        if self.sound:
            sounds = {'hit':0, 'hurt':1, 'gem':2, 'boost':3}
            for event in set(self.world.events):
                p.play(1 if event == 'hurt' else 0, sounds[event])

    def center(self, text, y, color=7):
        self.p.text((W-len(text)*4)//2, y, text, color)

    def button(self, text, y, color=12):
        p = self.p
        p.rect(36, y, W-72, 28, 1)
        p.rectb(36, y, W-72, 28, color)
        self.center(text, y+11, color)

    def ship(self, x, y, a, enemy=False):
        p = self.p
        ca, sa = math.cos(a), math.sin(a)
        c = 8 if enemy else 11
        p.circ(x, y, 7, 1)
        p.tri(x+ca*9, y+sa*9, x-ca*5-sa*6, y-sa*5+ca*6,
              x-ca*5+sa*6, y-sa*5-ca*6, c)
        p.line(x-ca*6-sa*5, y-sa*6+ca*5, x-ca*6+sa*5, y-sa*6-ca*5, 5)
        if not enemy:
            p.pset(round(x), round(y), 10)

    def blade(self, x, y, a, color):
        p = self.p
        ca, sa = math.cos(a), math.sin(a)
        p.tri(x+ca*8-sa*3, y+sa*8+ca*3,
              x+ca*8+sa*3, y+sa*8-ca*3,
              x+ca*LENGTH, y+sa*LENGTH, color)

    def draw(self):
        p, g = self.p, self.world
        p.cls(0)
        p.rect(0, FIELD_TOP, W, FIELD_BOTTOM-FIELD_TOP, 7)
        # Low-contrast technical geometry keeps bullets and the centre dot visible.
        for x in range(0, W, 40):
            p.line(x, FIELD_TOP, x, FIELD_BOTTOM-1, 13)
        for y in range(FIELD_TOP, FIELD_BOTTOM, 40):
            p.line(0, y, W-1, y, 13)
        p.circb(120, 135, 57, 13)
        p.circb(120, 135, 48, 13)
        p.circb(38, 244, 20, 13)
        p.rectb(175, 191, 48, 40, 13)
        for gem in g.gems:
            x, y = gem['x'], gem['y']
            if gem['life'] > FPS or p.frame_count % 8 < 4:
                p.tri(x, y-4, x-4, y, x+4, y, 11)
                p.tri(x, y+4, x-4, y, x+4, y, 11)
                p.pset(x, y-2, 7)
        for e in g.enemies:
            self.ship(e['x'], e['y'], math.pi/2, True)
        for x, y, a in g.trail[:-1]:
            self.blade(x, y, a, 13)
        self.blade(g.x, g.y, g.angle, 6)
        p.line(g.x+math.cos(g.angle)*8, g.y+math.sin(g.angle)*8,
               g.x+math.cos(g.angle)*LENGTH, g.y+math.sin(g.angle)*LENGTH, 12)
        for b in g.bullets:
            x, y, r = b['x'], b['y'], b['r']
            p.tri(x, y-r, x-r, y, x+r, y, 12)
            p.tri(x, y+r, x-r, y, x+r, y, 12)
            p.pset(x-1, y-1, 6)
        if g.state == 'play':
            self.ship(g.x, g.y, g.angle)
        for x, y, _, _, life, c in g.particles:
            p.pset(x, y, c)
        for x, y, text, life, c in g.labels:
            p.text(x, y, text, 1)
        # Field sprites never cover the controls.
        p.rect(0, 0, W, FIELD_TOP, 0)
        p.rect(0, FIELD_BOTTOM, W, H-FIELD_BOTTOM, 0)
        p.text(W-33, 14, 'SND' if self.sound else 'OFF', 11 if self.sound else 5)
        if self.screen == 'title':
            p.rect(20, 64, W-40, 205, 0)
            self.center('S W I N G  B L A D E', 78, 11)
            self.center('BULLETS / MULTIPLIER / GEMS', 96, 5)
            self.center('MOVE TO SWING THE BLADE', 121)
            self.center('BULLETS STAY. BLADE CONTACT: x+1', 139, 12)
            self.center('CENTRE DOT HIT = GAME OVER', 155, 10)
            self.button('START / SCORE ATTACK', 190, 11)
            self.button('INPUT TEST / PRACTICE', 232, 12)
            self.center('STICK / MOUSE / STOP TO FREEZE', 300, 5)
            self.center('v0.2.1 / INPUT TEST', 320, 5)
            return
        p.text(10, 14, 'II', 7)
        p.text(39, 14, 'MENU', 5)
        p.text(78, 8, f'{g.score:07}', 7)
        p.text(78, 22, f'x{g.multiplier:02}', 10)
        p.text(144, 22, f'LV {g.level}', 11)
        p.text(10, 287, f'{g.age/FPS:05.1f}s  KILLS {g.kills}  GEMS {g.gems_collected}', 5)
        p.circb(STICK_X, STICK_Y, STICK_RADIUS, 5)
        p.circb(STICK_X, STICK_Y, STICK_DEADZONE, 1)
        sx, sy = self.stick_vector
        p.circ(STICK_X+sx*24, STICK_Y+sy*24, 10, 11 if self.stick_active else 5)
        p.text(28, 384, 'MOVE', 5)
        p.text(103, 361, 'RELEASE: STOP', 11)
        p.text(103, 375, 'BLADE FREEZES', 5)
        if g.practice:
            p.rectb(140, 316, 86, 36, 12)
            p.text(156, 331, 'RESET / R', 12)
        else:
            p.text(110, 328, 'AVOID BLUE BULLETS', 12)
        if self.pause or g.state != 'play':
            p.rect(20, 83, W-40, 184, 0)
            p.rectb(20, 83, W-40, 184, 12)
            if self.pause:
                self.center('PAUSED', 128, 11)
                self.center('TAP II / PRESS P', 151)
                self.center('MENU: RETURN TO TITLE', 172, 5)
            else:
                self.center('GAME OVER', 103, 8)
                self.center(f'SCORE {g.score}', 128, 7)
                self.center(f'{g.age/FPS:.1f}s / LEVEL {g.level}', 148, 5)
                self.button('RETRY', 190, 11)
                self.button('TITLE', 232, 12)


if __name__ == '__main__':
    App()
