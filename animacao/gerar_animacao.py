"""Gera a animação "Leitura de equipamento no estoque" (30 s, em loop).

Uso:  python3 animacao/gerar_animacao.py
Saída: animacao/leitura-equipamento.mp4 e animacao/leitura-equipamento.gif
Requer: Pillow e ffmpeg.
"""
import math
import os
import random
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_DIR = os.path.dirname(os.path.abspath(__file__))
W, H = 1600, 900            # espaço de desenho ("design")
RS = 1.2                    # design -> render (1920x1080)
RW, RH = int(W * RS), int(H * RS)
FPS = 24
DUR = 30.0
STRIP = 132                 # altura da faixa branca (design)

# ---------------------------------------------------------------- paleta
NAVY = (31, 58, 92)
NAVY_D = (22, 41, 66)
TEAL = (93, 156, 136)       # botões do app
TEAL_L = (226, 240, 235)
GREEN = (52, 150, 82)
GREEN_L = (225, 244, 230)
BG = (240, 242, 243)
WALL = (236, 240, 241)
FLOOR = (214, 219, 222)
BLOB1 = (214, 235, 232)
BLOB2 = (210, 228, 240)
METAL = (110, 120, 132)
METAL_D = (84, 93, 104)
BOX = (214, 156, 98)
BOX_D = (186, 128, 74)
SKIN = (205, 145, 100)
SKIN_D = (176, 116, 76)
HAIR = (28, 20, 16)
HAIR_H = (58, 40, 30)
SHIRT = (30, 56, 98)
SHIRT_D = (22, 42, 76)
PANTS = (26, 38, 62)
TXT = (30, 45, 60)
GREY = (120, 128, 136)
WHITE = (255, 255, 255)
SW_BODY = (32, 37, 46)
SW_FACE = (44, 50, 61)

FONT_R = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}


def F(size, bold=False):
    k = (max(4, int(round(size))), bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FONT_B if bold else FONT_R, k[0])
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q, u):
    return (lerp(p[0], q[0], u), lerp(p[1], q[1], u))


def mix(c1, c2, u):
    return tuple(int(lerp(a, b, clamp(u))) for a, b in zip(c1, c2))


# ---------------------------------------------------------------- câmera
class Cam:
    """Mapeia coordenadas (mundo ou tela) para pixels."""

    def __init__(self, cx=800, cy=450, z=1.0, ox=W / 2, oy=H / 2, rs=RS):
        self.cx, self.cy, self.z, self.ox, self.oy, self.rs = cx, cy, z, ox, oy, rs

    def p(self, x, y):
        return ((x - self.cx) * self.z + self.ox) * self.rs, ((y - self.cy) * self.z + self.oy) * self.rs

    def l(self, v):
        return v * self.z * self.rs


ID = Cam()


def scr_cam(k):
    return Cam(0, 0, 1, 0, 0, k)


def rect(d, c, x0, y0, x1, y1, fill=None, r=0, outline=None, w=0):
    a = c.p(x0, y0)
    b = c.p(x1, y1)
    box = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
    rr = min(c.l(r), (box[2] - box[0]) / 2, (box[3] - box[1]) / 2)
    ww = int(round(c.l(w))) if w else 0
    if outline and ww < 1:
        ww = 1
    if rr > 0.5:
        d.rounded_rectangle(box, radius=rr, fill=fill, outline=outline, width=ww)
    else:
        d.rectangle(box, fill=fill, outline=outline, width=ww)


def ell(d, c, x, y, rx, ry=None, fill=None, outline=None, w=0):
    ry = rx if ry is None else ry
    a = c.p(x - rx, y - ry)
    b = c.p(x + rx, y + ry)
    ww = max(1, int(round(c.l(w)))) if outline else 0
    d.ellipse([a[0], a[1], b[0], b[1]], fill=fill, outline=outline, width=ww)


def poly(d, c, pts, fill=None, outline=None, w=0):
    pp = [c.p(x, y) for x, y in pts]
    if outline:
        d.polygon(pp, fill=fill, outline=outline, width=max(1, int(round(c.l(w)))))
    else:
        d.polygon(pp, fill=fill)


def line(d, c, pts, fill, w, round_=True):
    pp = [c.p(x, y) for x, y in pts]
    ww = max(1, int(round(c.l(w))))
    d.line(pp, fill=fill, width=ww, joint="curve")
    if round_:
        for x, y in pp:
            r = ww / 2
            d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def arc(d, c, x, y, rx, ry, a0, a1, fill, w):
    a = c.p(x - rx, y - ry)
    b = c.p(x + rx, y + ry)
    d.arc([a[0], a[1], b[0], b[1]], a0, a1, fill=fill, width=max(1, int(round(c.l(w)))))


def text(d, c, x, y, s, size, fill, bold=False, anchor="la"):
    d.text(c.p(x, y), s, font=F(c.l(size), bold), fill=fill, anchor=anchor)


def check(d, c, x, y, s, fill, w):
    line(d, c, [(x - s * 0.5, y), (x - s * 0.12, y + s * 0.38), (x + s * 0.55, y - s * 0.4)], fill, w)


# ---------------------------------------------------------------- QR code fictício
def make_qr(seed, n=21):
    rnd = random.Random(seed)
    m = [[rnd.random() < 0.48 for _ in range(n)] for _ in range(n)]

    def finder(ox, oy):
        for i in range(-1, 8):
            for j in range(-1, 8):
                x, y = ox + i, oy + j
                if 0 <= x < n and 0 <= y < n:
                    edge = i in (0, 6) or j in (0, 6)
                    core = 2 <= i <= 4 and 2 <= j <= 4
                    m[y][x] = (edge or core) and 0 <= i <= 6 and 0 <= j <= 6
    finder(0, 0)
    finder(n - 7, 0)
    finder(0, n - 7)
    return m


QR = {n: make_qr(n) for n in ("012958", "012959", "012960")}


def draw_qr(d, c, x, y, s, num):
    m = QR[num]
    n = len(m)
    cell = s / n
    rect(d, c, x, y, x + s, y + s, WHITE)
    for j in range(n):
        for i in range(n):
            if m[j][i]:
                rect(d, c, x + i * cell, y + j * cell, x + (i + 1) * cell + 0.3, y + (j + 1) * cell + 0.3, (20, 20, 20))


def ldc_logo(d, c, x, y, size, color=NAVY):
    """Marca genérica "LDC." em texto simples (como nas etiquetas do vídeo)."""
    text(d, c, x, y, "LDC.", size, color, True)


def draw_label(d, c, x, y, w, h, num, glow=0.0):
    """Etiqueta LDC: logo, número e QR code."""
    if glow > 0:
        g = 0.18 * h
        rect(d, c, x - g, y - g, x + w + g, y + h + g, mix(SW_FACE, (120, 230, 150), glow), r=h * 0.18)
    rect(d, c, x, y, x + w, y + h, WHITE, r=h * 0.06, outline=(200, 200, 200), w=h * 0.02)
    ldc_logo(d, c, x + w * 0.06, y + h * 0.1, h * 0.34)
    text(d, c, x + w * 0.06, y + h * 0.56, num, h * 0.24, (20, 20, 20), True)
    q = h * 0.8
    draw_qr(d, c, x + w - q - h * 0.1, y + h * 0.1, q, num)
    if glow > 0:
        rect(d, c, x - h * 0.06, y - h * 0.06, x + w + h * 0.06, y + h + h * 0.06, None, r=h * 0.12,
             outline=mix(WHITE, (40, 200, 90), glow), w=h * 0.07)


# ---------------------------------------------------------------- switch
def draw_switch(d, c, x, y, w, h, num, t, label_glow=0.0, seed=0):
    rect(d, c, x, y, x + w, y + h, SW_BODY, r=h * 0.08)
    rect(d, c, x + h * 0.08, y + h * 0.1, x + w - h * 0.08, y + h * 0.9, SW_FACE, r=h * 0.05)
    # portas (2 fileiras)
    pw = h * 0.16
    px0 = x + w * 0.06
    ncols = 12
    for row in range(2):
        for i in range(ncols):
            xx = px0 + i * pw * 1.45
            yy = y + h * (0.22 + row * 0.32)
            rect(d, c, xx, yy, xx + pw, yy + h * 0.22, (18, 20, 24))
            on = math.sin(t * (3 + (i * 7 + row * 3 + seed) % 5) + i + seed) > 0.1
            col = (90, 220, 110) if (i + row + seed) % 3 else (240, 170, 60)
            rect(d, c, xx + pw * 0.15, yy - h * 0.05, xx + pw * 0.45, yy - h * 0.02, col if on else (60, 66, 72))
    # etiqueta
    lw, lh = h * 1.55, h * 0.62
    lx, ly = x + w - lw - h * 0.35, y + (h - lh) / 2
    draw_label(d, c, lx, ly, lw, lh, num, label_glow)
    return (lx, ly, lw, lh)


SWITCHES = [("012959", 0), ("012958", 1), ("012960", 2)]  # de cima para baixo


# ---------------------------------------------------------------- cenário (mundo 1600x900)
FLOOR_Y = 600
CHAR_FEET = 712
SHELF_L = (60, 430)       # estante esquerda (x)
SHELF_BOARDS = [215, 335, 455, 575]
LAPTOP_SHELF = (330, 455)
TABLE = (1030, 1470, 478)  # x0, x1, topo
SW_W, SW_H = 380, 56


def switch_rects():
    x0 = (TABLE[0] + TABLE[1]) / 2 - SW_W / 2
    out = []
    for i, (num, seed) in enumerate(SWITCHES):
        y = TABLE[2] - (3 - i) * (SW_H + 2)
        out.append((x0, y, num, seed))
    return out


def draw_box(d, c, x, y, w, h):
    rect(d, c, x, y, x + w, y + h, BOX, r=3)
    rect(d, c, x, y, x + w, y + h * 0.18, BOX_D, r=3)
    rect(d, c, x + w * 0.45, y, x + w * 0.55, y + h, (230, 190, 140))
    rect(d, c, x + w * 0.12, y + h * 0.5, x + w * 0.36, y + h * 0.75, (240, 226, 200))


def draw_world(img, d, c, t, st):
    # parede e piso
    rect(d, c, -2000, -2000, 4000, FLOOR_Y, WALL)
    rect(d, c, -2000, FLOOR_Y, 4000, 3000, FLOOR)
    rect(d, c, -2000, FLOOR_Y - 6, 4000, FLOOR_Y + 4, (200, 206, 210))
    # manchas decorativas (como na ilustração do app)
    ell(d, c, 280, 330, 300, 230, BLOB1)
    ell(d, c, 1260, 300, 330, 220, BLOB2)
    ell(d, c, 760, 160, 150, 80, (226, 238, 236))
    # placa na parede
    rect(d, c, 640, 70, 960, 150, WHITE, r=14, outline=(205, 214, 220), w=3)
    text(d, c, 800, 92, "ESTOQUE DE TI", 26, NAVY, True, "mt")
    text(d, c, 800, 124, "ALTO ARAGUAIA", 18, TEAL, True, "mt")
    # estante esquerda
    x0, x1 = SHELF_L
    for xx in (x0, x1):
        rect(d, c, xx - 8, 110, xx + 8, FLOOR_Y + 10, METAL)
    for i, by in enumerate(SHELF_BOARDS):
        rect(d, c, x0 - 10, by, x1 + 10, by + 14, METAL_D if i % 2 else METAL, r=3)
    draw_box(d, c, 80, 135, 110, 80)
    draw_box(d, c, 200, 150, 90, 65)
    draw_box(d, c, 300, 125, 110, 90)
    # monitores
    for mx in (90, 250):
        rect(d, c, mx, 248, mx + 130, 320, (40, 44, 52), r=6)
        rect(d, c, mx + 8, 255, mx + 122, 312, (70, 110, 140), r=3)
        rect(d, c, mx + 55, 320, mx + 75, 335, (60, 64, 70))
    # caixas pequenas prateleira 3
    draw_box(d, c, 80, 395, 90, 60)
    draw_box(d, c, 180, 405, 70, 50)
    # gabinetes embaixo
    for mx in (85, 175, 265):
        rect(d, c, mx, 505, mx + 75, 575, (36, 40, 48), r=5)
        ell(d, c, mx + 37, 525, 6, 6, (90, 220, 110))
    # notebook na prateleira
    if st.get("laptop_on_shelf"):
        draw_laptop(d, c, LAPTOP_SHELF[0], LAPTOP_SHELF[1] - 2)
    # vaso de planta
    rect(d, c, 500, 560, 548, 610, (235, 235, 230), r=8)
    for a, l in ((-1.2, 60), (-0.6, 75), (0.0, 70), (0.6, 72), (1.1, 58)):
        ex, ey = 524 + math.sin(a) * l, 560 - math.cos(a) * l
        line(d, c, [(524, 560), (ex, ey)], (60, 130, 80), 14)
    # mesa com switches
    tx0, tx1, ty = TABLE
    rect(d, c, tx0, ty, tx1, ty + 18, METAL, r=4)
    rect(d, c, tx0 + 15, ty + 18, tx0 + 33, FLOOR_Y + 20, METAL_D)
    rect(d, c, tx1 - 33, ty + 18, tx1 - 15, FLOOR_Y + 20, METAL_D)
    rect(d, c, tx0 + 15, ty + 90, tx1 - 15, ty + 104, METAL)
    draw_box(d, c, tx0 + 60, ty + 104 - 70, 0, 0)  # (sem caixa)
    draw_box(d, c, tx0 + 50, ty + 30, 110, 60)
    draw_box(d, c, tx1 - 170, ty + 36, 120, 54)
    for i, (x, y, num, seed) in enumerate(switch_rects()):
        draw_switch(d, c, x, y, SW_W, SW_H, num, t, st.get("label_glow", 0) if i == 0 else 0, seed)
    # celulares na base (decoração em cima)
    for k in range(3):
        px = tx0 + 60 + k * 60
        rect(d, c, px, ty - 3 * (SW_H + 2) - 52, px + 34, ty - 3 * (SW_H + 2) - 4, (30, 34, 40), r=6)


def draw_laptop(d, c, x, y, tilt=0.0):
    """Notebook visto de trás (tampa), base em (x, y)."""
    w, h = 150, 96
    poly(d, c, [(x - w / 2 - 8, y), (x + w / 2 + 8, y), (x + w / 2, y - 10), (x - w / 2, y - 10)], (60, 64, 72))
    rect(d, c, x - w / 2, y - 10 - h, x + w / 2, y - 10, (58, 62, 70), r=8)
    rect(d, c, x - w / 2 + 6, y - 10 - h + 6, x + w / 2 - 6, y - 16, (74, 79, 88), r=6)
    ldc_logo(d, c, x - 18, y - 10 - h / 2 - 9, 15, (200, 205, 212))


# ---------------------------------------------------------------- personagem
CURLS = []
_r = random.Random(7)
for i in range(46):
    a = math.radians(_r.uniform(150, 390))
    rr = _r.uniform(0.75, 1.05)
    CURLS.append((math.cos(a) * 66 * rr, -22 + math.sin(a) * 66 * rr, _r.uniform(13, 20), _r.random() * 6.28))
SIDE_CURLS = []
for side in (-1, 1):
    for k in range(5):
        SIDE_CURLS.append((side * (50 + _r.uniform(-4, 10)), 0 + k * 17, _r.uniform(12, 16), _r.random() * 6.28))
BUN = [(_r.uniform(-30, 30), -78 + _r.uniform(-24, 10), _r.uniform(14, 20), _r.random() * 6.28) for _ in range(16)]


def ik(S, T, a, b, bend):
    dx, dy = T[0] - S[0], T[1] - S[1]
    dist = math.hypot(dx, dy)
    dist = clamp(dist, 1, a + b - 0.5)
    base = math.atan2(dy, dx)
    cosA = clamp((a * a + dist * dist - b * b) / (2 * a * dist), -1, 1)
    A = math.acos(cosA)
    ang = base + bend * A
    E = (S[0] + a * math.cos(ang), S[1] + a * math.sin(ang))
    H_ = (E[0] + b * math.cos(math.atan2(T[1] - E[1], T[0] - E[0])),
          E[1] + b * math.sin(math.atan2(T[1] - E[1], T[0] - E[0])))
    return E, H_


def draw_arm(d, c, S, T, bend):
    E, Hh = ik(S, T, 92, 96, bend)
    line(d, c, [S, E], SHIRT, 30)          # manga curta
    line(d, c, [lerp2(S, E, 0.55), E, Hh], SKIN, 22)
    line(d, c, [S, lerp2(S, E, 0.55)], SHIRT, 32)
    return Hh


def draw_hand(d, c, p, s=1.0):
    ell(d, c, p[0], p[1], 15 * s, 14 * s, SKIN)


def draw_char(img, d, c, t, st):
    x = st["x"]
    fy = CHAR_FEET
    bounce = st.get("bob", 0.0)
    lookx, looky = st.get("lookx", 0.0), st.get("looky", 0.0)
    smile = st.get("smile", 0.6)
    hx = x + lookx * 7
    hy = 262 + bounce + looky * 4
    hairamp = st.get("hairamp", 2.0)

    def curl(cx, cy, r, ph, col=HAIR):
        dy = math.sin(t * 7 + ph) * hairamp
        ell(d, c, cx, cy + dy, r, r, col)
        ell(d, c, cx - r * 0.25, cy + dy - r * 0.3, r * 0.35, r * 0.3, HAIR_H)

    # cabelo de trás + coque de cachos
    ell(d, c, hx, hy - 8, 66, 72, HAIR)
    for cx, cy, r, ph in BUN:
        curl(hx + cx + lookx * 3, hy + cy, r, ph)
    for cx, cy, r, ph in SIDE_CURLS:
        curl(hx + cx, hy + cy + 10, r, ph)
    # pernas
    wp = st.get("walk", None)
    for side in (-1, 1):
        hip = (x + side * 22, 512 + bounce)
        foot = [x + side * 26, fy]
        if wp is not None:
            foot[0] += math.sin(wp + (0 if side < 0 else math.pi)) * 32
            foot[1] -= max(0, math.cos(wp + (0 if side < 0 else math.pi))) * 14
        line(d, c, [hip, tuple(foot)], PANTS, 40)
        ell(d, c, foot[0] + side * 6, foot[1] + 6, 26, 12, (20, 22, 28))
    # tronco
    sy = 352 + bounce
    poly(d, c, [(x - 60, sy), (x + 60, sy), (x + 54, 528 + bounce), (x - 54, 528 + bounce)], SHIRT)
    rect(d, c, x - 56, 500 + bounce, x + 56, 530 + bounce, PANTS, r=6)
    rect(d, c, x - 56, 498 + bounce, x + 56, 506 + bounce, (15, 20, 30))
    # pescoço + gola
    rect(d, c, x - 14 + lookx * 3, 312 + bounce, x + 14 + lookx * 3, 360 + bounce, SKIN_D, r=6)
    poly(d, c, [(x - 30, sy - 2), (x, sy + 30), (x + 30, sy - 2), (x + 18, sy - 10), (x, sy + 12), (x - 18, sy - 10)], SHIRT_D)
    # crachá + cordão
    line(d, c, [(x - 16, sy + 2), (x + 4, sy + 92), (x + 18, sy + 2)], (20, 26, 40), 4, False)
    rect(d, c, x - 8, sy + 92, x + 16, sy + 124, WHITE, r=3)
    rect(d, c, x - 4, sy + 98, x + 12, sy + 108, TEAL)
    ldc_logo(d, c, x + 22, sy + 22, 13, (210, 220, 235))

    SL = (x - 58, 366 + bounce)
    SR = (x + 58, 366 + bounce)
    swing = math.sin(wp) * 20 if wp is not None else 0
    tL = st.get("handL") or (x - 72 + swing, 548 + bounce)
    tR = st.get("handR") or (x + 72 - swing, 548 + bounce)

    # notebook segurado
    lap = st.get("laptop")
    phone = st.get("phone")
    HL = draw_arm(d, c, SL, tL, st.get("bendL", -1))
    HR = draw_arm(d, c, SR, tR, st.get("bendR", 1))
    if lap:
        draw_laptop(d, c, lap[0], lap[1])
    if phone:
        draw_world_phone(img, c, phone)
    draw_hand(d, c, HL)
    draw_hand(d, c, HR)
    if st.get("pointR"):
        # dedo indicador estendido
        px, py = st["pointR"]
        line(d, c, [HR, (px, py)], SKIN, 9)

    # cabeça
    ell(d, c, hx - 41, hy + 6, 8, 11, SKIN_D)
    ell(d, c, hx + 41, hy + 6, 8, 11, SKIN_D)
    ell(d, c, hx - 41, hy + 18, 3, 3, (230, 190, 80))
    ell(d, c, hx + 41, hy + 18, 3, 3, (230, 190, 80))
    ell(d, c, hx, hy, 40, 48, SKIN)
    # rosto
    fx = hx + lookx * 9
    ey = hy - 2 + looky * 6
    for s in (-1, 1):
        exx = fx + s * 15
        if looky > 0.6:
            arc(d, c, exx, ey, 7, 4, 0, 180, (40, 25, 20), 3)
        else:
            ell(d, c, exx, ey, 6, 7.5, (40, 25, 20))
            ell(d, c, exx + 1.8 + lookx * 1.5, ey - 2.5, 2, 2, WHITE)
        arc(d, c, exx, ey - 14 + looky * 2, 9, 5, 200, 340, (40, 25, 20), 3)
        ell(d, c, fx + s * 25, hy + 16, 7, 4.5, (214, 128, 100))
    arc(d, c, fx, hy + 8, 4, 4, 20, 160, SKIN_D, 2.5)
    my = hy + 24 + looky * 2
    if smile > 0.8:
        a = c.p(fx - 12, my - 6)
        b = c.p(fx + 12, my + 10)
        d.chord([a[0], a[1], b[0], b[1]], 0, 180, fill=(120, 40, 40))
        a2 = c.p(fx - 9, my - 2)
        b2 = c.p(fx + 9, my + 4)
        d.chord([a2[0], a2[1], b2[0], b2[1]], 0, 180, fill=WHITE)
    else:
        arc(d, c, fx, my - 4, 10, 6 * smile + 1, 15, 165, (130, 50, 45), 3)
    # cachos da frente (franja)
    for i in range(9):
        a = math.radians(200 + i * 17.5)
        cx = hx + math.cos(a) * 40 + lookx * 2
        cy = hy - 14 + math.sin(a) * 40
        curl(cx, cy, 12 + (i % 3) * 2, i * 1.3)
    for s in (-1, 1):
        curl(hx + s * 44, hy - 2, 12, s * 2.0)
        curl(hx + s * 47, hy + 22, 11, s * 3.0)
    return (hx, hy)


# ---------------------------------------------------------------- celular
SWS, SHS = 360, 760        # coordenadas da tela do celular
SK = 2                     # resolução interna da tela


class Screen:
    def __init__(self, bg=WHITE):
        self.img = Image.new("RGB", (SWS * SK, SHS * SK), bg)
        self.d = ImageDraw.Draw(self.img)
        self.c = scr_cam(SK)


def status_bar(s, dark=False):
    col = WHITE if dark else TXT
    text(s.d, s.c, 22, 10, "10:42", 15, col, True)
    for i in range(4):
        rect(s.d, s.c, 290 + i * 7, 22 - i * 3, 294 + i * 7, 26, col)
    rect(s.d, s.c, 322, 13, 344, 25, None, r=3, outline=col, w=1.5)
    rect(s.d, s.c, 325, 16, 338, 22, col)


def app_header(s, title, sub=None):
    rect(s.d, s.c, 0, 0, SWS, 92, NAVY)
    status_bar(s, True)
    text(s.d, s.c, 22, 48, "LDC.", 26, WHITE, True)
    ell(s.d, s.c, 326, 62, 17, 17, (130, 170, 205))
    text(s.d, s.c, 326, 62, "IS", 13, WHITE, True, "mm")
    rect(s.d, s.c, 0, 92, SWS, 140, WHITE)
    text(s.d, s.c, 20, 104, title, 21, TXT, True)
    rect(s.d, s.c, 0, 140, SWS, 142, (225, 228, 232))


def nav_bar(s, active):
    rect(s.d, s.c, 0, SHS - 66, SWS, SHS, NAVY)
    for i, name in enumerate(("Início", "Escanear", "Registros")):
        x = 60 + i * 120
        col = WHITE if name == active else (170, 185, 205)
        text(s.d, s.c, x, SHS - 33, name, 16, col, name == active, "mm")
        if name == active:
            rect(s.d, s.c, x - 30, SHS - 66, x + 30, SHS - 62, TEAL)


def button(s, x0, y0, x1, y1, label, enabled=True, pressed=0.0, col=TEAL, size=21):
    base = col if enabled else (196, 202, 206)
    off = 3 * pressed
    if pressed > 0:
        base = mix(base, (40, 90, 80), 0.35 * pressed)
    rect(s.d, s.c, x0, y0 + off, x1, y1 + off, base, r=(y1 - y0) / 2)
    text(s.d, s.c, (x0 + x1) / 2, (y0 + y1) / 2 + off, label, size, WHITE, True, "mm")


def ripple(s, x, y, u):
    if 0 < u < 1:
        r = 18 + 40 * u
        rect(s.d, s.c, x - r, y - r, x + r, y + r, None, r=r, outline=mix(WHITE, TEAL, u), w=3 * (1 - u) + 1)


def screen_home(gps, valid, press=0.0, ripple_u=0.0):
    s = Screen((244, 246, 247))
    app_header(s, "Início")
    # mapa
    rect(s.d, s.c, 16, 156, SWS - 16, 352, (220, 236, 222), r=16)
    for k in range(5):
        line(s.d, s.c, [(16, 180 + k * 40), (SWS - 16, 170 + k * 44)], (245, 248, 245), 5, False)
    line(s.d, s.c, [(80, 156), (110, 250), (150, 352)], (245, 248, 245), 7, False)
    line(s.d, s.c, [(300, 156), (250, 230), (290, 352)], (160, 200, 230), 12, False)  # rio
    pin = mix((150, 156, 162), GREEN, gps)
    px, py = 180, 250
    if gps >= 1:
        pr = 20 + (valid * 30)
        ell(s.d, s.c, px, py + 18, pr, pr * 0.4, (190, 225, 200))
    ell(s.d, s.c, px, py - 14, 24, 24, pin)
    poly(s.d, s.c, [(px - 18, py - 2), (px + 18, py - 2), (px, py + 22)], pin)
    ell(s.d, s.c, px, py - 14, 9, 9, WHITE)
    # linha do toggle
    rect(s.d, s.c, 16, 366, SWS - 16, 430, WHITE, r=14)
    text(s.d, s.c, 34, 398, "Localização", 21, TXT, True, "lm")
    tx = lerp(276, 312, gps)
    rect(s.d, s.c, 260, 382, 330, 414, mix((200, 204, 208), GREEN, gps), r=16)
    ell(s.d, s.c, tx, 398, 13, 13, WHITE)
    # status
    if gps < 1:
        text(s.d, s.c, SWS / 2, 462, "GPS desativado", 22, GREY, False, "mm")
    else:
        text(s.d, s.c, SWS / 2, 462, "GPS ativado ✓", 26, GREEN, True, "mm")
    if valid > 0:
        y = 500 + (1 - ease(valid)) * 20
        col = mix((244, 246, 247), GREEN, ease(valid))
        rect(s.d, s.c, 16, y, SWS - 16, y + 92, mix((244, 246, 247), GREEN_L, ease(valid)), r=14)
        rect(s.d, s.c, 16, y, 24, y + 92, col)
        text(s.d, s.c, 40, y + 16, "ALTO ARAGUAIA", 25, mix((244, 246, 247), TXT, ease(valid)), True)
        text(s.d, s.c, 40, y + 54, "Localização validada", 19, col, True)
    button(s, 30, 616, SWS - 30, 674, "Ir para o Scan", valid >= 1, press, size=23)
    ripple(s, 180, 645, ripple_u)
    nav_bar(s, "Início")
    return s.img


def screen_scan(feed=None, scan_u=None, success=0.0):
    s = Screen((244, 246, 247))
    app_header(s, "Escanear Equipamento")
    rect(s.d, s.c, 16, 152, SWS - 16, 196, WHITE, r=10)
    rect(s.d, s.c, 16, 152, 22, 196, GREEN)
    text(s.d, s.c, 32, 174, "ALTO ARAGUAIA · validada", 16, TXT, True, "lm")
    fx0, fy0, fx1, fy1 = 26, 212, SWS - 26, 540
    frame_col = mix((150, 156, 162), (40, 190, 90), success)
    rect(s.d, s.c, fx0 - 6, fy0 - 6, fx1 + 6, fy1 + 6, frame_col, r=20)
    if feed is not None:
        fw, fh = int((fx1 - fx0) * SK), int((fy1 - fy0) * SK)
        s.img.paste(feed.resize((fw, fh), Image.LANCZOS), (int(fx0 * SK), int(fy0 * SK)))
    else:
        rect(s.d, s.c, fx0, fy0, fx1, fy1, (60, 64, 70))
    # cantos
    L = 34
    for (cx, cy, sx, sy) in ((fx0 + 18, fy0 + 18, 1, 1), (fx1 - 18, fy0 + 18, -1, 1),
                             (fx0 + 18, fy1 - 18, 1, -1), (fx1 - 18, fy1 - 18, -1, -1)):
        line(s.d, s.c, [(cx, cy + sy * L), (cx, cy), (cx + sx * L, cy)], WHITE if success < 0.5 else (90, 230, 120), 5)
    if scan_u is not None and success < 0.5:
        yy = lerp(fy0 + 30, fy1 - 30, scan_u)
        rect(s.d, s.c, fx0 + 14, yy - 2, fx1 - 14, yy + 2, (80, 240, 160))
    if success > 0:
        y = 560 + (1 - ease(success)) * 16
        rect(s.d, s.c, 30, y, SWS - 30, y + 60, mix((244, 246, 247), GREEN, ease(success)), r=30)
        text(s.d, s.c, SWS / 2, y + 30, "Placa 012959 ✓", 25, WHITE, True, "mm")
    else:
        text(s.d, s.c, SWS / 2, 580, "Aponte para a etiqueta LDC", 18, GREY, False, "mm")
    nav_bar(s, "Escanear")
    return s.img


def screen_status(instock=0.0, press_mail=0.0, rip1=0.0, rip2=0.0):
    s = Screen((244, 246, 247))
    app_header(s, "Escanear Equipamento")
    rect(s.d, s.c, 16, 152, SWS - 16, 232, WHITE, r=12)
    ell(s.d, s.c, 52, 192, 20, 20, GREEN)
    check(s.d, s.c, 52, 192, 20, WHITE, 4)
    text(s.d, s.c, 84, 166, "Placa lida", 15, GREY)
    text(s.d, s.c, 84, 186, "012959", 28, TXT, True)
    text(s.d, s.c, 20, 254, "Status do equipamento", 19, TXT, True)
    opts = ["In Stock", "In Use", "Reserved", "Broken"]
    for i, o in enumerate(opts):
        cx = 16 + (i % 2) * 168
        cy = 286 + (i // 2) * 76
        sel = instock if i == 0 else 0
        rect(s.d, s.c, cx, cy, cx + 160, cy + 64, mix(WHITE, GREEN_L, sel), r=12,
             outline=mix((215, 220, 224), GREEN, sel), w=2 + sel)
        text(s.d, s.c, cx + 16, cy + 32, o, 19, mix(TXT, GREEN, sel), sel > 0.5, "lm")
        if sel > 0.5:
            ell(s.d, s.c, cx + 136, cy + 32, 13, 13, GREEN)
            check(s.d, s.c, cx + 136, cy + 32, 13, WHITE, 3)
    ripple(s, 96, 318, rip1)
    button(s, 20, 470, SWS - 20, 534, "Abrir e-mail com a evidência", instock > 0.5, press_mail, size=18)
    ripple(s, 180, 502, rip2)
    nav_bar(s, "Escanear")
    return s.img


PHOTO = None


def screen_email(attach=0.0, press_send=0.0, rip=0.0):
    s = Screen(WHITE)
    rect(s.d, s.c, 0, 0, SWS, 100, (246, 247, 249))
    status_bar(s)
    text(s.d, s.c, 20, 58, "Novo e-mail", 22, TXT, True)
    off = 2 * press_send
    rect(s.d, s.c, 248, 48 + off, 344, 86 + off, mix((40, 110, 200), (20, 60, 130), press_send), r=19)
    text(s.d, s.c, 296, 67 + off, "Enviar", 18, WHITE, True, "mm")
    ripple(s, 296, 67, rip)
    rect(s.d, s.c, 0, 100, SWS, 102, (225, 228, 232))
    text(s.d, s.c, 20, 116, "Para:", 15, GREY)
    text(s.d, s.c, 74, 116, "inventario@empresa.com", 15, TXT)
    rect(s.d, s.c, 20, 144, SWS - 20, 145, (230, 232, 235))
    text(s.d, s.c, 20, 156, "Assunto:", 15, GREY)
    text(s.d, s.c, 20, 178, "DEVICE: Inventory Number|", 18, TXT, True)
    text(s.d, s.c, 20, 202, "012959|ALTO ARAGUAIA", 18, TXT, True)
    rect(s.d, s.c, 20, 234, SWS - 20, 235, (230, 232, 235))
    body = [("EQUIPAMENTO", True), ("Inventory Number: 012959", False), ("Status: In Stock", False),
            ("LOCAL", True), ("Unidade: ALTO ARAGUAIA", False), ("Localização validada", False),
            ("RESPONSÁVEL", True), ("Iza Silva", False)]
    for i, (ln, b) in enumerate(body):
        text(s.d, s.c, 20, 250 + i * 30, ln, 16, TXT if b else (80, 90, 100), b)
    if attach > 0:
        u = ease(attach)
        y = 512 + (1 - u) * 40
        rect(s.d, s.c, 20, y, SWS - 20, y + 92, mix(WHITE, (242, 245, 248), u), r=12,
             outline=mix(WHITE, (210, 216, 222), u), w=2)
        if PHOTO is not None and u > 0.05:
            th = PHOTO.resize((int(100 * SK), int(72 * SK)), Image.LANCZOS)
            s.img.paste(th, (int(30 * SK), int((y + 10) * SK)))
        text(s.d, s.c, 142, y + 22, "foto_012959.jpg", 17, mix(WHITE, TXT, u), True)
        text(s.d, s.c, 142, y + 50, "Imagem · 1,2 MB", 14, mix(WHITE, GREY, u))
    rect(s.d, s.c, 0, SHS - 60, SWS, SHS - 59, (225, 228, 232))
    text(s.d, s.c, 40, SHS - 30, "Anexar", 16, GREY, False, "lm")
    text(s.d, s.c, 230, SHS - 30, "Câmera", 16, GREY, False, "lm")
    return s.img


def screen_sent(u):
    s = Screen(WHITE)
    status_bar(s)
    k = ease(seg(u, 0, 0.5))
    k = k * (1 + 0.15 * math.sin(seg(u, 0.3, 0.6) * math.pi))
    r = 74 * k
    if r > 1:
        ell(s.d, s.c, SWS / 2, 300, r, r, GREEN)
        check(s.d, s.c, SWS / 2, 300, r * 1.0, WHITE, max(2, 14 * k))
    tu = ease(seg(u, 0.35, 0.8))
    text(s.d, s.c, SWS / 2, 430, "E-mail enviado", 30, mix(WHITE, GREEN, tu), True, "mm")
    text(s.d, s.c, SWS / 2, 474, "Leitura contabilizada", 22, mix(WHITE, TXT, tu), False, "mm")
    return s.img


def screen_registros():
    s = Screen((244, 246, 247))
    app_header(s, "Registros")
    rect(s.d, s.c, 16, 154, 176, 220, WHITE, r=12)
    text(s.d, s.c, 30, 166, "E-mails enviados", 14, GREY)
    text(s.d, s.c, 30, 186, "3", 24, TXT, True)
    rect(s.d, s.c, 184, 154, SWS - 16, 220, WHITE, r=12)
    text(s.d, s.c, 198, 166, "Unidade", 14, GREY)
    text(s.d, s.c, 198, 188, "ALTO ARAGUAIA", 15, TXT, True)
    rows = [("012959", "agora", True), ("012958", "10:31", False), ("012957", "10:18", False)]
    for i, (num, hh, hl) in enumerate(rows):
        y = 236 + i * 112
        rect(s.d, s.c, 16, y, SWS - 16, y + 100, GREEN_L if hl else WHITE, r=14,
             outline=GREEN if hl else (220, 224, 228), w=3 if hl else 1.5)
        text(s.d, s.c, 32, y + 14, num, 26 if hl else 22, TXT, True)
        text(s.d, s.c, 32, y + 52, "In Stock · " + hh, 16, GREY)
        rect(s.d, s.c, 214, y + 32, 330, y + 68, GREEN if hl else (232, 236, 238), r=18)
        text(s.d, s.c, 272, y + 50, "Enviado ✓", 16, WHITE if hl else GREEN, True, "mm")
    nav_bar(s, "Registros")
    return s.img


def make_phone(screen, wpx, back=False):
    """Retorna RGBA do celular com largura wpx (render px)."""
    hpx = int(wpx * 2.05)
    wpx = int(wpx)
    im = Image.new("RGBA", (wpx, hpx), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    r = wpx * 0.13
    d.rounded_rectangle([0, 0, wpx - 1, hpx - 1], radius=r, fill=(24, 26, 32, 255) if not back else (44, 48, 56, 255))
    if back:
        d.rounded_rectangle([wpx * 0.1, hpx * 0.05, wpx * 0.45, hpx * 0.22], radius=wpx * 0.06, fill=(30, 32, 38, 255))
        for (cx, cy) in ((0.2, 0.09), (0.35, 0.09), (0.2, 0.17)):
            rr = wpx * 0.055
            d.ellipse([wpx * cx - rr, hpx * cy - rr, wpx * cx + rr, hpx * cy + rr], fill=(10, 12, 16, 255))
        return im
    m = max(2, int(wpx * 0.045))
    sw, sh = wpx - 2 * m, hpx - 2 * m
    scr = screen.resize((sw, sh), Image.LANCZOS)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=r * 0.8, fill=255)
    im.paste(scr, (m, m), mask)
    d.rounded_rectangle([wpx * 0.36, m + 4, wpx * 0.64, m + 4 + wpx * 0.05], radius=wpx * 0.03, fill=(10, 10, 12, 255))
    return im


def paste_center(img, im, X, Y, angle=0.0):
    if angle:
        im = im.rotate(angle, resample=Image.BICUBIC, expand=True)
    img.paste(im, (int(X - im.width / 2), int(Y - im.height / 2)), im)


def draw_world_phone(img, c, ph):
    """ph: dict(pos=(x,y) mundo, w=largura mundo, screen=Image|None, back=bool, angle)."""
    X, Y = c.p(*ph["pos"])
    im = make_phone(ph.get("screen"), c.l(ph.get("w", 64)), ph.get("back", False))
    paste_center(img, im, X, Y, ph.get("angle", 0))


def phone_to_design(px, py, pw, sx, sy):
    """Converte ponto da tela do celular (sx, sy) para design, celular centrado em (px, py) com largura pw."""
    ph = pw * 2.05
    m = pw * 0.045
    x0 = px - pw / 2 + m
    y0 = py - ph / 2 + m
    return x0 + sx / SWS * (pw - 2 * m), y0 + sy / SHS * (ph - 2 * m)


# ---------------------------------------------------------------- mão em close
def draw_thumb(d, tip, base, press=0.0):
    c = ID
    mid = lerp2(base, tip, 0.55)
    mid = (mid[0] + 18, mid[1] + 10)
    line(d, c, [base, mid, tip], SKIN_D, 74)
    line(d, c, [base, mid, tip], SKIN, 64)
    ang = math.atan2(tip[1] - mid[1], tip[0] - mid[0])
    nx, ny = tip[0] - math.cos(ang) * 14, tip[1] - math.sin(ang) * 14
    ell(d, c, nx, ny, 17, 17, (232, 186, 160))
    if press > 0:
        ell(d, c, tip[0], tip[1], 40 + 10 * press, 40 + 10 * press, None, outline=mix(SKIN, WHITE, press), w=3)


def draw_holding_hand_back(d, px, py, pw):
    c = ID
    ph = pw * 2.05
    ell(d, c, px - pw * 0.15, py + ph * 0.48, pw * 0.48, ph * 0.2, SKIN)


def draw_holding_fingers(d, px, py, pw):
    c = ID
    ph = pw * 2.05
    for k in range(3):
        y = py + ph * (0.08 + k * 0.1)
        rect(d, c, px - pw / 2 - 26, y, px - pw / 2 + 22, y + 46, SKIN, r=22)
        rect(d, c, px - pw / 2 - 26, y, px - pw / 2 + 22, y + 46, None, r=22, outline=SKIN_D, w=2)


# ---------------------------------------------------------------- balões e faixa
def balloon(d, x, y, msg, u, tail=(-1, 1)):
    if u <= 0:
        return
    s = 0.6 + 0.4 * ease(u)
    c = Cam(x, y, s, x, y)
    f = F(c.l(34), True)
    tw = d.textlength(msg, font=f) / c.rs / s
    w, h = tw + 64, 84
    x0, y0 = x - w / 2, y - h / 2
    poly(d, c, [(x0 + 50, y0 + h - 4), (x0 + 30, y0 + h + 34), (x0 + 96, y0 + h - 4)], WHITE,
         outline=TEAL, w=3)
    rect(d, c, x0, y0, x0 + w, y0 + h, WHITE, r=26, outline=TEAL, w=4)
    rect(d, c, x0 + 46, y0 + h - 8, x0 + 100, y0 + h + 2, WHITE)
    text(d, c, x, y, msg, 34, TXT, True, "mm")


STEPS = [
    (0, 4, "Vamos registrar um equipamento."),
    (4, 9, "Ative a localização do celular."),
    (9, 13, "Toque em “Ir para o Scan”."),
    (13, 19, "Aponte a câmera para a etiqueta LDC."),
    (19, 22, "Escolha o status e abra o e-mail."),
    (22, 25, "Tire a foto com a etiqueta à vista."),
    (25, 28, "Toque em “Enviar”."),
    (28, 30, "Pronto! A leitura foi contabilizada."),
]


def draw_strip(d, t):
    c = ID
    y0 = H - STRIP
    rect(d, c, 0, y0 - 6, W, y0, (215, 220, 224))
    rect(d, c, 0, y0, W, H, WHITE)
    rect(d, c, 0, y0, 10, H, TEAL)
    idx = max(i for i, s in enumerate(STEPS) if t >= s[0])
    a, b, msg = STEPS[idx]
    u = ease(seg(t, a, a + 0.35))
    cy = y0 + STRIP / 2 + 4
    ell(d, c, 92, cy, 42, 42, NAVY)
    text(d, c, 92, cy, str(idx + 1), 40, WHITE, True, "mm")
    text(d, c, 160 + (1 - u) * 30, cy, msg, 46, mix(WHITE, TXT, u), True, "lm")
    text(d, c, W - 60, cy - 20, f"Passo {idx + 1} de 8", 26, (90, 100, 110), True, "rm")
    for i in range(8):
        col = TEAL if i <= idx else (210, 215, 220)
        ell(d, c, W - 60 - (7 - i) * 28, cy + 22, 8, 8, col)
    # barra de progresso
    rect(d, c, 0, y0, W * t / DUR, y0 + 6, TEAL)


# ---------------------------------------------------------------- cenas
def world_cam(t):
    if t < 4:
        return Cam(800, 420, 1.0)
    if t < 9:
        u = ease(seg(t, 4.0, 8.0))
        return Cam(lerp(800, 600, u), lerp(420, 395, u), lerp(1.0, 2.7, u))
    if 13 <= t < 15:
        x = char_x(t)
        return Cam(x + 120, 400, 1.6)
    if 22 <= t < 25:
        u = ease(seg(t, 22, 25))
        return Cam(lerp(1060, 1080, u), 380, lerp(1.9, 2.05, u))
    if t >= 28:
        u = ease(seg(t, 28, 29.4))
        return Cam(lerp(930, 800, u), lerp(390, 420, u), lerp(1.7, 1.0, u))
    return Cam(800, 420, 1.0)


def char_x(t):
    return lerp(560, 900, ease(seg(t, 13.0, 15.0)))


SCREENS = {}


def cached(key, fn):
    if key not in SCREENS:
        SCREENS[key] = fn()
    return SCREENS[key]


def q(v, n=20):
    return round(v * n) / n


def char_state(t):
    x = char_x(t)
    st = {"x": x, "smile": 0.6, "hairamp": 2.0}
    if t < 4:
        lap = (x - 20, 488)
        st["laptop"] = lap
        st["handL"] = (lap[0] - 62, lap[1] + 6)
        look = ease(seg(t, 0.6, 1.2))
        st["looky"] = 1 - look
        st["smile"] = lerp(0.5, 1.0, ease(seg(t, 1.0, 1.6)))
        st["hairamp"] = 2 + 3 * look
        if t < 1.3:
            st["handR"] = (lap[0] + 40, lap[1] - 2)
        else:
            w = ease(seg(t, 1.3, 1.8)) * (1 - ease(seg(t, 3.4, 3.9)))
            wave = math.sin((t - 1.3) * 10) * 26
            st["handR"] = lerp2((lap[0] + 40, lap[1] - 2), (x + 128 + wave, 248), w)
            st["bendR"] = 1
        st["bob"] = math.sin(t * 2) * 1.5
    elif t < 9:
        # coloca o notebook na prateleira
        u = ease(seg(t, 4.0, 5.3))
        held = (x - 20, 488)
        shelf = (LAPTOP_SHELF[0], LAPTOP_SHELF[1] - 2)
        if t < 5.3:
            lap = (lerp(held[0], shelf[0], u), lerp(held[1], shelf[1], u) - math.sin(u * math.pi) * 40)
            st["laptop"] = lap
            st["handL"] = (lap[0] - 30 if u > 0.4 else lap[0] - 62, lap[1] + 6)
        else:
            st["laptop_on_shelf"] = True
            r = ease(seg(t, 5.3, 6.4))
            st["handL"] = lerp2((shelf[0] - 30, shelf[1] + 6), (x + 2, 470), r)
        # tira o celular do bolso
        pocket = (x + 50, 540)
        chest = (x + 18, 405)
        if t < 4.8:
            st["handR"] = None
        elif t < 5.6:
            st["handR"] = lerp2((x + 72, 548), pocket, ease(seg(t, 4.8, 5.5)))
        else:
            v = ease(seg(t, 5.6, 6.5))
            ppos = lerp2(pocket, chest, v)
            gps = ease(seg(t, 7.1, 7.5))
            valid = ease(seg(t, 8.0, 8.5))
            scr = cached(("home", q(gps), q(valid)), lambda: screen_home(q(gps), q(valid)))
            st["phone"] = {"pos": ppos, "w": 72, "screen": scr}
            if t < 6.6:
                st["handR"] = (ppos[0] + 22, ppos[1] + 40)
            else:
                # dedo desliza o botão de localização
                tog = lambda sx: phone_xy(chest, 72, sx, 398)
                if t < 7.0:
                    a = ease(seg(t, 6.6, 7.0))
                    st["handR"] = lerp2((x + 70, 470), (tog(276)[0] + 10, tog(276)[1] + 22), a)
                    st["pointR"] = None
                elif t < 7.8:
                    g = ease(seg(t, 7.1, 7.5))
                    tip = tog(lerp(276, 312, g))
                    st["handR"] = (tip[0] + 14, tip[1] + 26)
                    st["pointR"] = tip
                else:
                    a = ease(seg(t, 7.8, 8.3))
                    tip = tog(312)
                    st["handR"] = lerp2((tip[0] + 14, tip[1] + 26), (x + 78, 470), a)
            st["handL"] = (chest[0] - 6, chest[1] + 62) if t > 6.4 else st["handL"]
        st["looky"] = 0.7 if t > 6.2 else 0.2
        st["smile"] = 0.9 if t > 8.0 else 0.6
    elif 13 <= t < 15:
        st["laptop_on_shelf"] = True
        st["walk"] = (t - 13.0) * 7.0 if t < 14.8 else None
        st["bob"] = -abs(math.sin((t - 13) * 7.0)) * 6 if t < 14.8 else 0
        chest = (x + 18, 405)
        scr = cached(("scan_idle",), lambda: screen_scan(None, None, 0))
        st["phone"] = {"pos": chest, "w": 72, "screen": scr}
        st["handL"] = (chest[0] - 6, chest[1] + 62)
        st["lookx"] = 0.8
        st["hairamp"] = 4
    elif 22 <= t < 25:
        st["laptop_on_shelf"] = True
        st["lookx"] = 1.0
        st["smile"] = 0.7
        reach = ease(seg(t, 22.0, 22.6))
        hand = lerp2((x + 72, 548), (x + 182, 344), reach)
        st["handR"] = hand
        st["bendR"] = 1
        st["phone"] = {"pos": (hand[0] + 6, hand[1] - 30), "w": 46, "back": True, "angle": -8}
    elif t >= 28:
        st["laptop_on_shelf"] = True
        hold = (x - 104, 298)
        st["handL"] = (hold[0], hold[1] + 62)
        st["bendL"] = -1
        st["phone"] = {"pos": hold, "w": 84, "screen": cached(("reg",), screen_registros)}
        wave = math.sin((t - 28) * 10) * 24
        w = ease(seg(t, 28.5, 29.0))
        st["handR"] = lerp2((x + 72, 548), (x + 128 + wave, 250), w)
        st["smile"] = 1.0
        st["hairamp"] = 4
    else:
        st["laptop_on_shelf"] = True
    return st


def phone_xy(center, pw, sx, sy):
    return phone_to_design_world(center, pw, sx, sy)


def phone_to_design_world(center, pw, sx, sy):
    ph = pw * 2.05
    m = pw * 0.045
    return (center[0] - pw / 2 + m + sx / SWS * (pw - 2 * m),
            center[1] - ph / 2 + m + sy / SHS * (ph - 2 * m))


def render_world(t, extra_st=None):
    img = Image.new("RGB", (RW, RH), BG)
    d = ImageDraw.Draw(img)
    c = world_cam(t)
    st = char_state(t)
    if extra_st:
        st.update(extra_st)
    draw_world(img, d, c, t, st)
    head = draw_char(img, d, c, t, st)
    return img, d, c, head


# ---- composições em close
BLUR_CACHE = {}


def blurred_world(key, cam, st):
    if key not in BLUR_CACHE:
        img = Image.new("RGB", (RW, RH), BG)
        d = ImageDraw.Draw(img)
        draw_world(img, d, cam, 0.0, st)
        if key == "chest":
            # silhueta dela atrás (fora de foco)
            d2 = d
            ell(d2, cam, 600, 260, 70, 80, HAIR)
            poly(d2, cam, [(520, 352), (680, 352), (700, 560), (500, 560)], SHIRT)
            ell(d2, cam, 600, 270, 42, 50, SKIN)
        BLUR_CACHE[key] = img.filter(ImageFilter.GaussianBlur(26 * RS))
    return BLUR_CACHE[key].copy()


def switches_close(t, glow=0.0, scan_u=None):
    """Close na frente da pilha de switches (design)."""
    img = Image.new("RGB", (RW, RH), WALL)
    d = ImageDraw.Draw(img)
    c = ID
    ell(d, c, 300, 200, 500, 300, BLOB1)
    ell(d, c, 1300, 250, 420, 260, BLOB2)
    rect(d, c, -10, 760, W + 10, H, METAL)
    sw_h = 205
    x0, x1 = 50, 1190
    lab = None
    for i, (num, seed) in enumerate(SWITCHES):
        y = 120 + i * (sw_h + 8)
        r = draw_switch(d, c, x0, y, x1 - x0, sw_h, num, t, glow if i == 0 else 0, seed)
        if i == 0:
            lab = r
    if scan_u is not None and glow < 0.5:
        lx, ly, lw, lh = lab
        qs = lh * 0.8
        qx = lx + lw - qs - lh * 0.1
        yy = ly + lh * 0.1 + qs * scan_u
        rect(d, c, qx - 14, yy - 4, qx + qs + 14, yy + 4, (60, 240, 150))
        rect(d, c, qx - 14, yy - 12, qx + qs + 14, yy - 4, (150, 245, 200))
    return img, lab


def shot_closeup_phone(t, screen, tip=None, press=0.0, bg="chest", ots=False):
    if bg == "chest":
        img = blurred_world("chest", Cam(600, 380, 2.4), {"laptop_on_shelf": True})
    else:
        img = BLUR_CACHE_SW.copy()
    d = ImageDraw.Draw(img)
    if ots:
        # ombro e cachos dela em primeiro plano (por cima do ombro)
        ell(d, ID, 120, 980, 420, 330, SHIRT)
        ell(d, ID, 40, 300, 260, 420, HAIR)
        rr = random.Random(3)
        for k in range(26):
            cx, cy = rr.uniform(-60, 270), rr.uniform(-40, 700)
            ell(d, ID, cx, cy + math.sin(t * 5 + k) * 3, rr.uniform(26, 44), None, HAIR)
            ell(d, ID, cx - 8, cy - 10, 10, 8, HAIR_H)
    pw = 330
    px, py = 820, 410 + math.sin(t * 1.3) * 4
    draw_holding_hand_back(d, px, py, pw)
    im = make_phone(screen, pw * RS)
    paste_center(img, im, px * RS, py * RS)
    draw_holding_fingers(d, px, py, pw)
    if tip is not None:
        tx, ty = phone_to_design(px, py, pw, tip[0], tip[1])
        draw_thumb(d, (tx, ty), (px + 330, py + 520), press)
    return img, d, (px, py, pw)


BLUR_CACHE_SW = None


def tap(t, t_down, dur=0.18):
    """Retorna intensidade do toque (0..1) em torno de t_down."""
    return clamp(1 - abs(t - t_down) / dur)


def thumb_path(t, pts):
    """pts: lista de (tempo, (sx, sy)). Interpola posição do polegar."""
    if t <= pts[0][0]:
        return pts[0][1]
    for (ta, pa), (tb, pb) in zip(pts, pts[1:]):
        if t <= tb:
            return lerp2(pa, pb, ease(seg(t, ta, tb)))
    return pts[-1][1]


REST = (330, 720)
AWAY = (420, 900)


def render(t):
    global BLUR_CACHE_SW
    # ---------- passo 1, 2
    if t < 9 or 13 <= t < 15 or 22 <= t < 25 or t >= 28:
        img, d, c, head = render_world(t)
        if t < 4:
            hx, hy = c.p(*head)
            balloon(d, hx / RS + 250, hy / RS - 150, "Oi! Vamos fazer uma leitura?", seg(t, 1.5, 1.9))
        if 22 <= t < 25:
            # flash
            fl = clamp(1 - abs(t - 23.4) / 0.18)
            if fl > 0:
                x, y, num, seed = switch_rects()[0]
                lx, ly = c.p(x + SW_W - 100, y + SW_H / 2)
                glow = Image.new("L", (RW, RH), 0)
                gd = ImageDraw.Draw(glow)
                R = c.l(260)
                gd.ellipse([lx - R, ly - R, lx + R, ly + R], fill=int(255 * fl))
                glow = glow.filter(ImageFilter.GaussianBlur(R / 3))
                img = Image.composite(Image.new("RGB", (RW, RH), WHITE), img, glow)
                img = Image.blend(img, Image.new("RGB", (RW, RH), WHITE), 0.35 * fl)
                d = ImageDraw.Draw(img)
            # PIP: foto anexada ao e-mail
            pu = ease(seg(t, 23.8, 24.2))
            if pu > 0:
                att = q(ease(seg(t, 24.1, 24.6)))
                scr = cached(("mail", att, 0, 0), lambda: screen_email(att))
                im = make_phone(scr, 200 * RS)
                X, Y = lerp(-200, 140, pu) * RS, 360 * RS
                paste_center(img, im, X, Y)
        if t >= 28:
            hx, hy = c.p(*head)
            balloon(d, hx / RS + 300, hy / RS - 40, "Pronto! Leitura enviada ✓", seg(t, 28.6, 29.0))
    # ---------- passo 3: Ir para o Scan
    elif t < 13:
        btn = (180, 645)
        tip = thumb_path(t, [(9.0, REST), (9.6, REST), (10.2, btn), (10.7, btn), (11.2, REST)])
        pr = tap(t, 10.35, 0.2)
        if t < 10.6:
            scr = cached(("home_p", q(pr)), lambda: screen_home(1, 1, q(pr), 0))
        else:
            u = ease(seg(t, 10.6, 11.0))
            a = cached(("home_p", 0), lambda: screen_home(1, 1, 0, 0))
            b = cached(("scan_idle",), lambda: screen_scan(None, None, 0))
            scr = slide(a, b, q(u))
        img, d, _ = shot_closeup_phone(t, scr, tip, pr)
    # ---------- passo 4: leitura da etiqueta (close nos switches)
    elif t < 19:
        succ = ease(seg(t, 17.3, 17.6))
        scan_u = (math.sin((t - 15.6) * 2.8 - math.pi / 2) + 1) / 2 if t > 15.6 else None
        base, lab = switches_close(t, succ, scan_u)
        if BLUR_CACHE_SW is None:
            BLUR_CACHE_SW = base.filter(ImageFilter.GaussianBlur(24 * RS))
        lx, ly, lw, lh = lab
        cx, cy = (lx + lw / 2) * RS, (ly + lh / 2) * RS
        fw, fh = 300 * RS * 1.5, 328 * RS * 1.5
        feed = base.crop((int(cx - fw / 2), int(cy - fh / 2), int(cx + fw / 2), int(cy + fh / 2)))
        scr = screen_scan(feed, scan_u, succ)
        img = base
        d = ImageDraw.Draw(img)
        u = ease(seg(t, 15.0, 15.7))
        px, py = lerp(1900, 1400, u), lerp(760, 430, u)
        pw = 300
        ell(d, ID, px + 20, py + 340, 170, 120, SKIN)  # mão
        im = make_phone(scr, pw * RS)
        paste_center(img, im, px * RS, py * RS, -4)
        for k in range(3):
            rect(d, ID, px + pw / 2 - 20, py + 80 + k * 64, px + pw / 2 + 26, py + 128 + k * 64, SKIN, r=22)
        if succ > 0:
            lab_txt = "Placa 012959 ✓"
            bx, by = lx + lw / 2, ly - 48
            k2 = ease(succ)
            ff = F(ID.l(34), True)
            tw = d.textlength(lab_txt, font=ff) / RS
            rect(d, ID, bx - tw / 2 - 24, by - 30, bx + tw / 2 + 24, by + 30, mix(WHITE, GREEN, k2), r=30)
            text(d, ID, bx, by, lab_txt, 34, WHITE, True, "mm")
        if t < 15.0:
            # caminhada já tratada acima; não ocorre
            pass
    # ---------- passo 5: status + abrir e-mail (por cima do ombro)
    elif t < 22:
        if BLUR_CACHE_SW is None:
            base, _ = switches_close(0, 0, None)
            BLUR_CACHE_SW = base.filter(ImageFilter.GaussianBlur(24 * RS))
        b1 = (96, 318)
        b2 = (180, 502)
        tip = thumb_path(t, [(19.0, REST), (19.3, REST), (19.6, b1), (19.9, b1), (20.3, b2), (20.75, b2), (21.2, REST)])
        p1 = tap(t, 19.68, 0.16)
        p2 = tap(t, 20.5, 0.18)
        ins = 1.0 if t > 19.7 else 0.0
        if t < 20.75:
            scr = cached(("status", ins, q(p2), q(seg(t, 19.68, 20.1)) if t > 19.68 else 0),
                         lambda: screen_status(ins, q(p2), q(seg(t, 19.68, 20.1)) if t > 19.68 else 0))
        else:
            u = ease(seg(t, 20.75, 21.1))
            a = cached(("status_end",), lambda: screen_status(1, 0))
            b = cached(("mail", 0, 0, 0), lambda: screen_email(0))
            scr = slide(a, b, q(u))
        img, d, _ = shot_closeup_phone(t, scr, tip, max(p1, p2), bg="sw", ots=True)
    # ---------- passo 7: enviar
    elif 25 <= t < 28:
        send = (296, 67)
        tip = thumb_path(t, [(25.0, REST), (25.25, REST), (25.6, send), (25.85, send), (26.3, AWAY)])
        pr = tap(t, 25.7, 0.15)
        if t < 25.9:
            scr = cached(("mail", 1, q(pr), q(seg(t, 25.7, 26.0))), lambda: screen_email(1, q(pr), q(seg(t, 25.7, 26.0))))
        else:
            u = q(seg(t, 26.0, 27.0), 24)
            scr = cached(("sent", u), lambda: screen_sent(u))
        img, d, (px, py, pw) = shot_closeup_phone(t, scr, tip, pr)
        # aviãozinho de papel
        pu = seg(t, 25.8, 27.2)
        if 0 < pu < 1:
            sx, sy = phone_to_design(px, py, pw, *send)
            ex, ey = 1700, -120
            cx1, cy1 = sx + 300, sy + 220
            pts = []
            for k in range(0, 21):
                v = pu * k / 20
                bx = (1 - v) ** 2 * sx + 2 * (1 - v) * v * cx1 + v * v * ex
                by = (1 - v) ** 2 * sy + 2 * (1 - v) * v * cy1 + v * v * ey
                pts.append((bx, by))
            for k in range(0, len(pts) - 1, 2):
                line(d, ID, [pts[k], pts[k + 1]], (150, 190, 180), 5)
            bx, by = pts[-1]
            ang = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0]) if pu > 0.01 else -0.5
            s = 60 * (0.6 + pu)
            ca, sa = math.cos(ang), math.sin(ang)

            def R(px_, py_):
                return (bx + px_ * ca - py_ * sa, by + px_ * sa + py_ * ca)
            poly(d, ID, [R(s, 0), R(-s * 0.7, -s * 0.6), R(-s * 0.35, 0)], WHITE, outline=TEAL, w=3)
            poly(d, ID, [R(s, 0), R(-s * 0.35, 0), R(-s * 0.7, s * 0.45)], (225, 236, 233), outline=TEAL, w=3)
    else:
        img, d, c, head = render_world(t)

    d = ImageDraw.Draw(img)
    draw_strip(d, t)
    return img


def slide(a, b, u):
    if u <= 0:
        return a
    if u >= 1:
        return b
    out = a.copy()
    w = a.width
    off = int(w * u)
    out.paste(a.crop((off, 0, w, a.height)), (0, 0))
    out.paste(b.crop((0, 0, off, b.height)), (w - off, 0))
    return out


def main():
    global PHOTO
    # foto do equipamento (para o anexo do e-mail)
    base, lab = switches_close(0.0)
    lx, ly, lw, lh = lab
    cx, cy = (lx + lw / 2) * RS, (ly + lh / 2) * RS
    PHOTO = base.crop((int(cx - 420), int(cy - 300), int(cx + 420), int(cy + 300)))

    mp4 = os.path.join(OUT_DIR, "leitura-equipamento.mp4")
    gif = os.path.join(OUT_DIR, "leitura-equipamento.gif")
    n = int(DUR * FPS)
    fade = int(0.5 * FPS)
    first = None
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20",
         "-movflags", "+faststart", mp4], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        fr = render(t).resize((1280, 720), Image.LANCZOS)
        if i == 0:
            first = fr
        if i >= n - fade:   # funde com o 1º quadro para o loop ficar suave
            fr = Image.blend(fr, first, (i - (n - fade) + 1) / (fade + 1))
        proc.stdin.write(fr.tobytes())
        if i % 48 == 0:
            print(f"{t:5.1f}s", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf",
         "fps=12,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=192:stats_mode=diff[p];"
         "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
         "-loop", "0", gif], check=True)
    print("ok:", mp4, gif)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        PHOTO = None
        base, lab = switches_close(0.0)
        lx, ly, lw, lh = lab
        cx, cy = (lx + lw / 2) * RS, (ly + lh / 2) * RS
        PHOTO = base.crop((int(cx - 420), int(cy - 300), int(cx + 420), int(cy + 300)))
        out = sys.argv[2]
        times = [float(v) for v in sys.argv[3:]]
        thumbs = [render(t).resize((640, 360), Image.LANCZOS) for t in times]
        cols = 3
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 640, rows * 360), WHITE)
        for k, th in enumerate(thumbs):
            sheet.paste(th, ((k % cols) * 640, (k // cols) * 360))
        sheet.save(out)
    else:
        main()
