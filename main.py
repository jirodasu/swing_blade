# title: SWING BLADE - prototype
# author: jirodasu
# version: 0.1.0
"""60 FPS inertial blade prototype. No external assets required."""
import math
import random

W, H, FPS = 180, 320, 60
LENGTH = 35
ROUND_FRAMES = 30 * FPS


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def segment_distance(x, y, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = clamp(((x - ax) * dx + (y - ay) * dy) / max(dx * dx + dy * dy, .0001), 0, 1)
    return math.hypot(x - ax - t * dx, y - ay - t * dy)


class World:
    def __init__(self, practice=False, seed=None):
        self.rng = random.Random(seed)
        self.practice = practice
        self.x, self.y = 90., 154.
        self.vx = self.vy = self.omega = 0.
        self.angle = math.pi / 2
        self.age = self.kills = self.invul = self.freeze = 0
        self.hp = 5
        self.state = 'play'
        self.enemies = []
        self.particles = []
        self.trail = []
        self.events = []
        if practice:
            self.enemies = [dict(x=x, y=y, hp=1, r=6, speed=0., cool=0, kind=0)
                            for x, y in [(45., 110.), (135., 110.), (90., 215.)]]

    def spawn(self):
        edge = self.rng.randrange(4)
        if edge < 2:
            x, y = (6 if edge == 0 else W - 6), self.rng.uniform(55, 252)
        else:
            x, y = self.rng.uniform(10, W - 10), (49 if edge == 2 else 256)
        tough = self.age > 12 * FPS and self.rng.random() < .24
        self.enemies.append(dict(x=x, y=y, r=7 if tough else 5,
                                 hp=2 if tough else 1, kind=int(tough), cool=0,
                                 speed=.25 + self.age / ROUND_FRAMES * .18))

    def burst(self, x, y, color, count=9):
        for _ in range(count):
            a = self.rng.uniform(0, math.tau)
            s = self.rng.uniform(.4, 2.0)
            self.particles.append([x, y, math.cos(a)*s, math.sin(a)*s, 18, color])

    def step(self, ux, uy):
        self.events = []
        if self.state != 'play':
            return
        if self.freeze:
            self.freeze -= 1
            return
        self.age += 1
        self.invul = max(0, self.invul - 1)
        ox, oy, oa = self.x, self.y, self.angle
        old_vx, old_vy = self.vx, self.vy
        n = max(1., math.hypot(ux, uy))
        self.vx += (ux/n*1.55 - self.vx) * .22
        self.vy += (uy/n*1.55 - self.vy) * .22
        self.x = clamp(self.x + self.vx, 10, W - 10)
        self.y = clamp(self.y + self.vy, 54, 250)
        self.vx, self.vy = self.x - ox, self.y - oy
        ax, ay = self.vx - old_vx, self.vy - old_vy
        # Acceleration pushes the blade opposite travel; angular momentum survives a turn.
        self.omega += (math.sin(self.angle)*ax - math.cos(self.angle)*ay) * .24
        speed = math.hypot(self.vx, self.vy)
        if speed > .08:
            target = math.atan2(-self.vy, -self.vx)
            error = wrap(target - self.angle)
            if abs(error) > 3.10:
                error = math.copysign(abs(error), self.omega if abs(self.omega) > .002 else 1)
            self.omega += error * .013 * min(1, speed)
        self.omega = clamp(self.omega * .50, -.30, .30)
        self.angle = wrap(self.angle + self.omega)
        self.trail.append((self.x + math.cos(self.angle)*LENGTH, self.y + math.sin(self.angle)*LENGTH))
        self.trail = self.trail[-10:]
        if not self.practice and self.age % max(24, 80 - self.age//40) == 0 and len(self.enemies) < 45:
            self.spawn()
        power = abs(self.omega)*LENGTH + speed
        for e in self.enemies:
            e['cool'] = max(0, e['cool']-1)
            dx, dy = self.x-e['x'], self.y-e['y']
            d = max(.001, math.hypot(dx, dy))
            e['x'] += dx/d * e['speed']
            e['y'] += dy/d * e['speed']
            hit = False
            # Sample the swept blade, including the moving pivot, to prevent tunnelling.
            if power > 1.8 and not e['cool']:
                for k in range(7):
                    t = k/6
                    a = oa + wrap(self.angle-oa)*t
                    px, py = ox+(self.x-ox)*t, oy+(self.y-oy)*t
                    if segment_distance(e['x'], e['y'], px+math.cos(a)*9, py+math.sin(a)*9,
                                        px+math.cos(a)*LENGTH, py+math.sin(a)*LENGTH) < e['r']+3:
                        hit = True
                        break
            if hit:
                e['hp'] -= 1
                e['cool'] = 18
                e['x'] = clamp(e['x']-dx/d*7, 3, W-3)
                e['y'] = clamp(e['y']-dy/d*7, 46, 258)
                self.burst(e['x'], e['y'], 10)
                self.events.append('hit')
                self.freeze = 2
                if e['hp'] <= 0:
                    self.kills += 1
            elif e['hp'] > 0 and d < e['r']+5 and not self.invul and not self.practice:
                self.hp -= 1
                self.invul = 75
                self.burst(self.x, self.y, 8, 15)
                self.events.append('hurt')
        self.enemies = [e for e in self.enemies if e['hp'] > 0]
        for p in self.particles:
            p[0] += p[2]
            p[1] += p[3]
            p[4] -= 1
        self.particles = [p for p in self.particles if p[4] > 0]
        if self.practice and not self.enemies:
            self.enemies = [dict(x=x, y=y, hp=1, r=6, speed=0., cool=0, kind=0)
                            for x, y in [(45., 110.), (135., 110.), (90., 215.)]]
        if self.hp <= 0:
            self.state = 'lose'
        elif not self.practice and self.age >= ROUND_FRAMES:
            self.state = 'win'


class App:
    def __init__(self):
        import pyxel
        self.p = pyxel
        pyxel.init(W, H, title='SWING BLADE / jirodasu', fps=FPS, quit_key=pyxel.KEY_NONE)
        pyxel.colors[12] = 0x43DED0
        pyxel.colors[1] = 0x142632
        pyxel.colors[5] = 0x6C8597
        pyxel.mouse(True)
        pyxel.sounds[0].set('c3g3c4', 'n', '653', 'f', 3)
        pyxel.sounds[1].set('c2a1', 'p', '65', 'f', 6)
        self.sound = True
        self.screen = 'title'
        self.world = World(True)
        self.anchor = None
        self.pause = False
        self.input_lock = False
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
        self.anchor = None
        self.input_lock = True

    def update(self):
        p = self.p
        if self.web is not None and int(self.web.swingBlurCount) != self.blur_seen:
            self.blur_seen = int(self.web.swingBlurCount)
            self.anchor = None
            self.input_lock = True
            if self.screen == 'game' and self.world.state == 'play':
                self.pause = True
        tap = p.btnp(p.MOUSE_BUTTON_LEFT)
        mx, my = p.mouse_x, p.mouse_y
        if p.btnp(p.KEY_M) or (tap and mx > 150 and my < 35):
            self.sound = not self.sound
        if self.screen == 'title':
            self.world.x = 90 + math.sin(p.frame_count*.035)*8
            self.world.y = 134 + math.cos(p.frame_count*.035)*5
            self.world.angle = p.frame_count*.045
            self.world.trail.append((self.world.x+math.cos(self.world.angle)*LENGTH,
                                     self.world.y+math.sin(self.world.angle)*LENGTH))
            self.world.trail = self.world.trail[-10:]
            if p.btnp(p.KEY_RETURN) or (tap and 185 <= my <= 221):
                self.start(False)
            elif p.btnp(p.KEY_T) or (tap and 230 <= my <= 258):
                self.start(True)
            return
        if self.world.state != 'play':
            if p.btnp(p.KEY_RETURN) or (tap and 185 <= my <= 221):
                self.start(self.world.practice)
            elif p.btnp(p.KEY_ESCAPE) or (tap and 230 <= my <= 258):
                self.screen = 'title'
                self.world = World(True)
            return
        if p.btnp(p.KEY_ESCAPE):
            self.screen = 'title'
            self.world = World(True)
            self.anchor = None
            return
        if p.btnp(p.KEY_P) or (tap and mx < 32 and my < 35):
            self.pause = not self.pause
            self.anchor = None
            self.input_lock = True
        if self.pause:
            return
        if self.input_lock:
            if p.btn(p.MOUSE_BUTTON_LEFT):
                return
            self.input_lock = False
        ux = int(p.btn(p.KEY_RIGHT) or p.btn(p.KEY_D))-int(p.btn(p.KEY_LEFT) or p.btn(p.KEY_A))
        uy = int(p.btn(p.KEY_DOWN) or p.btn(p.KEY_S))-int(p.btn(p.KEY_UP) or p.btn(p.KEY_W))
        if tap and my >= 44:
            self.anchor = (mx, my)
        if not p.btn(p.MOUSE_BUTTON_LEFT):
            self.anchor = None
        if self.anchor:
            dx, dy = mx-self.anchor[0], my-self.anchor[1]
            d = math.hypot(dx, dy)
            if d > 3:
                scale = min(1, (d-3)/19)/d
                ux, uy = dx*scale, dy*scale
            else:
                ux = uy = 0
        self.world.step(ux, uy)
        if self.sound:
            for event in set(self.world.events):
                p.play(0 if event == 'hit' else 1, 0 if event == 'hit' else 1)

    def center(self, text, y, color=7):
        self.p.text((W-len(text)*4)//2, y, text, color)

    def button(self, text, y, color):
        p = self.p
        p.rect(25, y, 130, 28, 1)
        p.rectb(25, y, 130, 28, color)
        self.center(text, y+11, color)

    def draw(self):
        p, g = self.p, self.world
        p.cls(0)
        for x in range(0, W, 12):
            for y in range(44, 262, 12):
                p.pset(x, y, 1)
        p.rectb(3, 44, W-6, 218, 1)
        for i in range(1, len(g.trail)):
            p.line(*g.trail[i-1], *g.trail[i], 1 if i < 6 else 12)
        for e in (g.enemies if self.screen == 'game' else []):
            c = 7 if e['cool'] > 12 else (9 if e['kind'] else 8)
            p.circ(e['x'], e['y'], e['r'], 2)
            p.circb(e['x'], e['y'], e['r'], c)
            p.pset(e['x']-2, e['y']-1, 7)
            p.pset(e['x']+2, e['y']-1, 7)
            if e['kind']:
                p.rect(e['x']-3, e['y']+2, e['hp']*3, 1, c)
        a = g.angle
        ca, sa = math.cos(a), math.sin(a)
        x, y = g.x, g.y
        p.line(x, y, x+ca*12, y+sa*12, 4)
        p.tri(x+ca*11-sa*3, y+sa*11+ca*3,
              x+ca*11+sa*3, y+sa*11-ca*3, x+ca*LENGTH, y+sa*LENGTH, 7)
        p.line(x+ca*11, y+sa*11, x+ca*LENGTH, y+sa*LENGTH, 12)
        if not g.invul or p.frame_count % 8 < 4:
            p.circ(x, y, 6, 1)
            p.circ(x, y, 4, 12)
            p.pset(x-1, y-2, 7)
        for px, py, _, _, life, c in g.particles:
            p.rect(px, py, 2 if life > 8 else 1, 2 if life > 8 else 1, c)
        p.rect(0, 0, W, 43, 0)
        p.rect(0, 263, W, 57, 0)
        p.text(154, 14, 'SND' if self.sound else 'OFF', 12 if self.sound else 5)
        if self.screen == 'title':
            p.rect(10, 50, 160, 40, 0)
            self.center('S W I N G  B L A D E', 58, 12)
            self.center('INERTIA / SURVIVAL', 75, 5)
            self.button('START / 30 SEC', 190, 12)
            self.button('PRACTICE / NO DAMAGE', 230, 5)
            self.center('DRAG TO MOVE', 275, 7)
            self.center('TURN SHARPLY TO SWING', 289, 12)
            self.center('v0.1 / jirodasu', 306, 5)
            return
        p.text(10, 14, 'II', 7)
        self.center('PRACTICE' if g.practice else f'{max(0, 30-g.age/FPS):04.1f}s', 10, 7)
        for i in range(5):
            p.rect(62+i*12, 26, 9, 3, 12 if i < g.hp else 1)
        p.text(10, 272, f'HITS {g.kills:03}', 5)
        self.center('DRAG / WASD / ARROWS', 306, 5)
        power = min(1, abs(g.omega)/.18)
        p.text(113, 272, 'SWING', 12)
        p.rect(112, 282, 55, 3, 1)
        p.rect(112, 282, int(55*power), 3, 12 if power < .8 else 10)
        if self.anchor:
            ax, ay = self.anchor
            p.circb(ax, ay, 22, 5)
            dx, dy = p.mouse_x-ax, p.mouse_y-ay
            n = max(1, math.hypot(dx, dy)/20)
            p.circ(ax+dx/n, ay+dy/n, 5, 12)
        if self.pause or g.state != 'play':
            p.rect(12, 92, 156, 170, 0)
            p.rectb(12, 92, 156, 170, 12)
            if self.pause:
                self.center('PAUSED', 131, 12)
                self.center('TAP II / PRESS P', 156, 7)
            else:
                self.center('SURVIVED!' if g.state == 'win' else 'TRY AGAIN', 119, 12 if g.state == 'win' else 8)
                self.center(f'TIME {min(30, g.age/FPS):.1f}s  HITS {g.kills}', 147, 7)
                self.button('RETRY', 190, 12)
                self.button('TITLE', 230, 5)


if __name__ == '__main__':
    App()
