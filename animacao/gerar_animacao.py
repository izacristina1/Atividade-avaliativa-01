"""Gera a animação "Leitura de equipamento no estoque" (30 s, em loop).

Formato de vídeo-tutorial de app: à esquerda, o cenário real (ilustração e
foto do estoque usadas no app); à direita, um celular com as telas do app
recriadas e um indicador de toque mostrando cada interação.

Uso:  python3 animacao/gerar_animacao.py            -> MP4 + GIF
      python3 animacao/gerar_animacao.py preview saida.png 1.0 5.0 ...
Requer: Pillow e ffmpeg.
"""
import math
import os
import random
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
W, H = 1600, 900            # espaço de desenho
RS = 1.2                    # -> render 1920x1080
RW, RH = int(W * RS), int(H * RS)
FPS = 24
DUR = 30.0
STRIP = 120

# ------------------------------------------------------------------ paleta do app
NAVY = (36, 66, 99)
NAVY_D = (27, 50, 77)
TEAL = (95, 158, 137)
TEAL_D = (70, 128, 110)
GREEN = (60, 140, 80)
GREEN_L = (227, 242, 231)
BLUE = (37, 99, 200)
BG1 = (244, 246, 247)
BG2 = (232, 238, 240)
TXT = (32, 46, 60)
GREY = (118, 126, 134)
LINE = (224, 228, 232)
WHITE = (255, 255, 255)
SW_BODY = (30, 34, 42)
SW_FACE = (42, 47, 57)

FR = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
_fc = {}


def F(size, bold=False):
    k = (max(4, int(round(size))), bold)
    if k not in _fc:
        _fc[k] = ImageFont.truetype(FB if bold else FR, k[0])
    return _fc[k]


def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = clamp(x)
    return 1 - (1 - x) ** 3


def seg(t, a, b):
    return clamp((t - a) / (b - a))


def lerp(a, b, u):
    return a + (b - a) * u


def lerp2(p, q_, u):
    return (lerp(p[0], q_[0], u), lerp(p[1], q_[1], u))


def mix(c1, c2, u):
    u = clamp(u)
    return tuple(int(round(lerp(a, b, u))) for a, b in zip(c1[:3], c2[:3]))


def q(v, n=24):
    return round(v * n) / n


# ------------------------------------------------------------------ desenho
class Cam:
    def __init__(self, k=RS):
        self.k = k

    def p(self, x, y):
        return x * self.k, y * self.k

    def l(self, v):
        return v * self.k


ID = Cam()


def rect(d, c, x0, y0, x1, y1, fill=None, r=0, outline=None, w=0):
    a, b = c.p(x0, y0), c.p(x1, y1)
    box = [min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])]
    rr = min(c.l(r), (box[2] - box[0]) / 2, (box[3] - box[1]) / 2)
    ww = max(1, int(round(c.l(w)))) if outline else 0
    if rr > 0.5:
        d.rounded_rectangle(box, radius=rr, fill=fill, outline=outline, width=ww)
    else:
        d.rectangle(box, fill=fill, outline=outline, width=ww)


def ell(d, c, x, y, rx, ry=None, fill=None, outline=None, w=0):
    ry = rx if ry is None else ry
    a, b = c.p(x - rx, y - ry), c.p(x + rx, y + ry)
    d.ellipse([a[0], a[1], b[0], b[1]], fill=fill, outline=outline,
              width=max(1, int(round(c.l(w)))) if outline else 0)


def poly(d, c, pts, fill=None):
    d.polygon([c.p(x, y) for x, y in pts], fill=fill)


def line(d, c, pts, fill, w):
    pp = [c.p(x, y) for x, y in pts]
    ww = max(1, int(round(c.l(w))))
    d.line(pp, fill=fill, width=ww, joint="curve")
    for x, y in pp:
        r = ww / 2
        d.ellipse([x - r, y - r, x + r, y + r], fill=fill)


def text(d, c, x, y, s, size, fill, bold=False, anchor="la"):
    d.text(c.p(x, y), s, font=F(c.l(size), bold), fill=fill, anchor=anchor)


def tlen(d, c, s, size, bold=False):
    return d.textlength(s, font=F(c.l(size), bold)) / c.k


def check(d, c, x, y, s, fill, w):
    line(d, c, [(x - s * 0.45, y + s * 0.02), (x - s * 0.12, y + s * 0.33), (x + s * 0.48, y - s * 0.35)], fill, w)


def soft_shadow(size, radius, blur, alpha=70):
    w, h = size
    pad = int(blur * 3)
    im = Image.new("L", (w + 2 * pad, h + 2 * pad), 0)
    ImageDraw.Draw(im).rounded_rectangle([pad, pad, pad + w, pad + h], radius=radius, fill=alpha)
    return im.filter(ImageFilter.GaussianBlur(blur)), pad


# ------------------------------------------------------------------ etiqueta/switch (visão da câmera)
def make_qr(seed, n=21):
    rnd = random.Random(seed)
    m = [[rnd.random() < 0.48 for _ in range(n)] for _ in range(n)]
    for ox, oy in ((0, 0), (n - 7, 0), (0, n - 7)):
        for i in range(-1, 8):
            for j in range(-1, 8):
                x, y = ox + i, oy + j
                if 0 <= x < n and 0 <= y < n:
                    inside = 0 <= i <= 6 and 0 <= j <= 6
                    m[y][x] = inside and (i in (0, 6) or j in (0, 6) or (2 <= i <= 4 and 2 <= j <= 4))
    return m


QRS = {k: make_qr(k) for k in ("012959", "012958", "012960")}


def draw_label(d, c, x, y, w, h, num):
    rect(d, c, x, y, x + w, y + h, WHITE, r=h * 0.05)
    text(d, c, x + w * 0.06, y + h * 0.1, "LDC.", h * 0.34, NAVY, True)
    text(d, c, x + w * 0.06, y + h * 0.58, num, h * 0.23, (20, 20, 20), True)
    qs = h * 0.8
    qx, qy = x + w - qs - h * 0.1, y + h * 0.1
    m = QRS[num]
    n = len(m)
    cell = qs / n
    for j in range(n):
        for i in range(n):
            if m[j][i]:
                rect(d, c, qx + i * cell, qy + j * cell, qx + (i + 1) * cell + 0.25, qy + (j + 1) * cell + 0.25, (18, 18, 18))
    return (qx, qy, qs)


def draw_switch(d, c, x, y, w, h, num, t, seed):
    rect(d, c, x, y, x + w, y + h, SW_BODY, r=h * 0.06)
    rect(d, c, x + h * 0.07, y + h * 0.1, x + w - h * 0.07, y + h * 0.9, SW_FACE, r=h * 0.04)
    pw = h * 0.15
    for row in range(2):
        for i in range(12):
            xx = x + w * 0.05 + i * pw * 1.42
            yy = y + h * (0.24 + row * 0.32)
            rect(d, c, xx, yy, xx + pw, yy + h * 0.21, (16, 18, 22))
            on = math.sin(t * (3 + (i * 7 + row * 3 + seed) % 5) + i + seed) > 0.1
            col = (90, 220, 110) if (i + row + seed) % 3 else (240, 170, 60)
            rect(d, c, xx + pw * 0.15, yy - h * 0.06, xx + pw * 0.45, yy - h * 0.025, col if on else (60, 66, 72))
    lw, lh = h * 1.55, h * 0.62
    lx, ly = x + w - lw - h * 0.3, y + (h - lh) / 2
    qr = draw_label(d, c, lx, ly, lw, lh, num)
    return (lx, ly, lw, lh), qr


def camera_view(t, size, flash=0.0):
    """Visão da câmera do celular apontada para a pilha de switches (360 de largura lógica)."""
    w, h = size
    k = w / 360.0
    img = Image.new("RGB", (w, h), (198, 210, 214))
    d = ImageDraw.Draw(img)
    c = Cam(k)
    rect(d, c, -10, 40, 30, 2000, (120, 128, 138))
    rect(d, c, 338, 40, 380, 2000, (120, 128, 138))
    sh = 128
    top = max(70, (h / k) / 2 - 200)
    lab = None
    for i, (num, seed) in enumerate((("012958", 1), ("012959", 0), ("012960", 2))):
        y = top + i * (sh + 10)
        r = draw_switch(d, c, -150, y, 520, sh, num, t, seed)
        if num == "012959":
            lab = r
        rect(d, c, -20, y + sh + 1, 380, y + sh + 9, (130, 138, 148))
    img = img.filter(ImageFilter.GaussianBlur(0.5 * k))
    if flash > 0:
        img = Image.blend(img, Image.new("RGB", img.size, WHITE), flash)
    return img, lab


# ------------------------------------------------------------------ telas do app
SWS, SHS = 360, 780
SK = 2.2


class Screen:
    def __init__(self, bg=BG1):
        self.img = Image.new("RGB", (int(SWS * SK), int(SHS * SK)), bg)
        self.d = ImageDraw.Draw(self.img)
        self.c = Cam(SK)


def status_bar(s, light=True):
    col = WHITE if light else TXT
    text(s.d, s.c, 26, 18, "10:42", 14, col, True)
    for i in range(4):
        rect(s.d, s.c, 276 + i * 6, 29 - i * 3, 280 + i * 6, 32, col)
    rect(s.d, s.c, 306, 20, 328, 32, None, r=3, outline=col, w=1.3)
    rect(s.d, s.c, 308.5, 22.5, 322, 29.5, col, r=1)
    rect(s.d, s.c, 329, 24, 331, 28, col)


def app_header(s, title=None, back=False):
    rect(s.d, s.c, 0, 0, SWS, 104, NAVY)
    status_bar(s)
    text(s.d, s.c, 18, 58, "LDC", 30, WHITE, True)
    text(s.d, s.c, 18 + tlen(s.d, s.c, "LDC", 30, True), 58, ".", 30, (150, 200, 120), True)
    text(s.d, s.c, 292, 64, "Iza Silva", 14, WHITE, True, "rm")
    ell(s.d, s.c, 246, 84, 3.5, 3.5, (120, 210, 120))
    text(s.d, s.c, 292, 84, "Online", 11, (150, 210, 150), True, "rm")
    ell(s.d, s.c, 324, 74, 18, 18, (120, 160, 196))
    text(s.d, s.c, 324, 74, "IS", 13, WHITE, True, "mm")
    if title:
        rect(s.d, s.c, 0, 104, SWS, 146, WHITE)
        if back:
            text(s.d, s.c, 16, 125, "←", 18, TXT, True, "lm")
            text(s.d, s.c, 42, 125, title, 17, TXT, True, "lm")
            ell(s.d, s.c, 334, 125, 11, 11, None, TXT, 1.6)
            text(s.d, s.c, 334, 125, "?", 13, TXT, True, "mm")
        else:
            text(s.d, s.c, 16, 125, title, 17, TXT, True, "lm")
        rect(s.d, s.c, 0, 145, SWS, 146, LINE)


def nav_bar(s, active):
    rect(s.d, s.c, 0, SHS - 74, SWS, SHS, NAVY)
    for i, name in enumerate(("Início", "Escanear", "Registros")):
        x = 60 + i * 120
        on = name == active
        text(s.d, s.c, x, SHS - 46, name, 14, WHITE if on else (165, 182, 202), on, "mm")
        if on:
            rect(s.d, s.c, x - 28, SHS - 74, x + 28, SHS - 71, TEAL)
    rect(s.d, s.c, 120, SHS - 12, 240, SHS - 8, (200, 210, 222), r=2)


def loc_card(s, y, h=46):
    rect(s.d, s.c, 12, y, SWS - 12, y + h, WHITE, r=8, outline=LINE, w=1)
    rect(s.d, s.c, 12, y + 2, 16, y + h - 2, GREEN)
    text(s.d, s.c, 26, y + 9, "ALTO ARAGUAIA", 13, TXT, True)
    text(s.d, s.c, 26, y + 27, "Localização validada", 11, GREEN)


def pill_button(s, x0, y0, x1, y1, label, fill, fg=WHITE, size=16, press=0.0):
    off = 1.5 * press
    col = mix(fill, (0, 0, 0), 0.18 * press)
    rect(s.d, s.c, x0, y0 + off, x1, y1 + off, col, r=(y1 - y0) / 2)
    text(s.d, s.c, (x0 + x1) / 2, (y0 + y1) / 2 + off, label, size, fg, True, "mm")


_THUMB = {}


def scene_thumb(wpx, hpx):
    key = (wpx, hpx)
    if key not in _THUMB:
        _THUMB[key] = ILL.resize((wpx, hpx), Image.LANCZOS)
    return _THUMB[key]


def scr_home(gps=0.0, valid=0.0, press=0.0):
    s = Screen()
    app_header(s, "Início", back=True)
    y = 156
    vu = ease(valid)
    rect(s.d, s.c, 12, y, SWS - 12, y + 58, WHITE, r=8, outline=LINE, w=1)
    rect(s.d, s.c, 12, y + 2, 16, y + 56, mix((190, 196, 202), GREEN, max(gps, vu)))
    pin = mix((168, 174, 180), GREEN, gps)
    ell(s.d, s.c, 40, y + 24, 9, 9, pin)
    poly(s.d, s.c, [(32, y + 28), (48, y + 28), (40, y + 42)], pin)
    ell(s.d, s.c, 40, y + 24, 3.5, 3.5, WHITE)
    if vu < 0.5:
        text(s.d, s.c, 58, y + 12, "Localização do celular", 13, TXT, True)
        if gps < 1:
            text(s.d, s.c, 58, y + 33, "GPS desativado", 12, GREY)
        else:
            text(s.d, s.c, 58, y + 33, "GPS ativado ✓", 12, GREEN, True)
        tx = lerp(290, 316, gps)
        rect(s.d, s.c, 280, y + 17, 330, y + 41, mix((205, 209, 213), GREEN, gps), r=12)
        ell(s.d, s.c, tx, y + 29, 10, 10, WHITE)
    else:
        a = ease((vu - 0.5) * 2)
        text(s.d, s.c, 58, y + 12, "ALTO ARAGUAIA • Operational G&O", 12, mix(WHITE, TXT, a), True)
        text(s.d, s.c, 58, y + 33, "Localização validada • a 0,5 km", 11, mix(WHITE, GREEN, a))
    text(s.d, s.c, SWS / 2, 252, "Controle de Estoque de TI", 20, NAVY_D, True, "mm")
    text(s.d, s.c, SWS / 2, 282, "Leia a placa de patrimônio, escolha o status", 10.5, GREY, False, "mm")
    text(s.d, s.c, SWS / 2, 298, "e envie o e-mail com a foto do equipamento.", 10.5, GREY, False, "mm")
    tw, th = int(336 * SK), int(192 * SK)
    th_img = scene_thumb(tw, th)
    mask = Image.new("L", (tw, th), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, tw - 1, th - 1], radius=int(10 * SK), fill=255)
    s.img.paste(th_img, (int(12 * SK), int(318 * SK)), mask)
    en = vu > 0.5
    pill_button(s, 18, 556, SWS - 18, 610, "Ir para o Scan", TEAL if en else (180, 196, 190), size=19, press=press)
    o = 1.5 * press
    rect(s.d, s.c, 70, 574 + o, 88, 592 + o, None, r=2, outline=WHITE, w=1.6)
    rect(s.d, s.c, 70, 582 + o, 88, 584 + o, WHITE)
    text(s.d, s.c, SWS / 2, 640, "Dúvidas? Toque em “?” no alto da tela.", 10.5, GREY, False, "mm")
    nav_bar(s, "Início")
    return s.img


def scr_scan(press=0.0):
    s = Screen()
    app_header(s, "Escanear Equipamento")
    loc_card(s, 156)
    rect(s.d, s.c, 12, 214, SWS - 12, 478, (52, 56, 62), r=12)
    L = 30
    for cx, cy, sx, sy in ((92, 254, 1, 1), (268, 254, -1, 1), (92, 380, 1, -1), (268, 380, -1, -1)):
        line(s.d, s.c, [(cx, cy + sy * L), (cx, cy), (cx + sx * L, cy)], (220, 224, 228), 4)
    text(s.d, s.c, SWS / 2, 306, "Aponte a câmera para o", 13, (220, 224, 228), True, "mm")
    text(s.d, s.c, SWS / 2, 326, "QR code do equipamento", 13, (220, 224, 228), True, "mm")
    pill_button(s, 46, 412, SWS - 46, 452, "Toque para escanear", (40, 92, 160), size=14, press=press)
    rect(s.d, s.c, 12, 494, SWS - 12, 538, WHITE, r=22, outline=LINE, w=1.4)
    text(s.d, s.c, SWS / 2, 516, "Digitar o número da placa", 14, NAVY_D, True, "mm")
    nav_bar(s, "Escanear")
    return s.img


def scr_reading(t, u, success):
    """Câmera lendo o QR code."""
    s = Screen((0, 0, 0))
    view_img, lab = camera_view(t, (int(SWS * SK), int(SHS * SK)))
    s.img.paste(view_img, (0, 0))
    s.d = ImageDraw.Draw(s.img)
    (lx, ly, lw, lh), (qx, qy, qs) = lab
    status_bar(s, light=False)
    fx0, fy0, fx1, fy1 = lx - 16, ly - 16, lx + lw + 16, ly + lh + 16
    col = mix((235, 238, 240), (60, 220, 110), success)
    for (cx, cy, sx, sy) in ((fx0, fy0, 1, 1), (fx1, fy0, -1, 1), (fx0, fy1, 1, -1), (fx1, fy1, -1, -1)):
        line(s.d, s.c, [(cx, cy + sy * 22), (cx, cy), (cx + sx * 22, cy)], col, 4)
    if success > 0:
        rect(s.d, s.c, lx - 5, ly - 5, lx + lw + 5, ly + lh + 5, None, r=6,
             outline=mix(WHITE, (50, 200, 100), success), w=4)
    elif u is not None:
        yy = qy + qs * u
        rect(s.d, s.c, qx - 10, yy - 1.5, qx + qs + 10, yy + 1.5, (70, 240, 150))
    msg = "QR code lido" if success > 0.5 else "Lendo QR code..."
    tw_ = tlen(s.d, s.c, msg, 13, True)
    rect(s.d, s.c, SWS / 2 - tw_ / 2 - 16, 54, SWS / 2 + tw_ / 2 + 16, 84, (20, 22, 26), r=15)
    text(s.d, s.c, SWS / 2, 69, msg, 13, WHITE, True, "mm")
    if success > 0:
        r = 26 * ease_out(success)
        ell(s.d, s.c, SWS / 2, 640, r, r, GREEN)
        if r > 8:
            check(s.d, s.c, SWS / 2, 640, r * 0.9, WHITE, 4)
    return s.img


def scr_plate(instock=0.0, press_ins=0.0, press_mail=0.0):
    s = Screen()
    app_header(s, "Escanear Equipamento")
    loc_card(s, 156)
    y = 212
    rect(s.d, s.c, 12, y, SWS - 12, y + 62, WHITE, r=8, outline=LINE, w=1)
    ell(s.d, s.c, 38, y + 31, 14, 14, GREEN)
    check(s.d, s.c, 38, y + 31, 14, WHITE, 3)
    text(s.d, s.c, 60, y + 12, "Placa lida", 10, GREY)
    text(s.d, s.c, 60, y + 26, "012959", 22, TXT, True)
    rect(s.d, s.c, 266, y + 18, 336, y + 44, (232, 238, 236), r=13)
    text(s.d, s.c, 301, y + 31, "Editar", 12, TXT, True, "mm")
    text(s.d, s.c, 14, 296, "Status do Equipamento", 14, TXT, True)
    opts = [("", "In Stock"), ("In Stock >", "Reserved"), ("In Stock >", "To Refresh"), ("In Stock >", "Broken")]
    for i, (small, big) in enumerate(opts):
        x0 = 12 + (i % 2) * 172
        y0 = 320 + (i // 2) * 62
        sel = instock if i == 0 else 0.0
        pr = 1.5 * press_ins if i == 0 else 0.0
        rect(s.d, s.c, x0, y0 + pr, x0 + 164, y0 + 52 + pr, mix(WHITE, GREEN_L, sel), r=7,
             outline=mix(LINE, GREEN, sel), w=1 + 1.2 * sel)
        if small:
            text(s.d, s.c, x0 + 12, y0 + 10, small, 9.5, GREY)
            text(s.d, s.c, x0 + 12, y0 + 24, big, 13, TXT, True)
        else:
            text(s.d, s.c, x0 + 12, y0 + 26 + pr, big, 13, mix(TXT, GREEN, sel), True, "lm")
        if sel > 0.5:
            check(s.d, s.c, x0 + 142, y0 + 26 + pr, 12, GREEN, 2.6)
    en = instock > 0.5
    pill_button(s, 14, 464, SWS - 14, 506, "Abrir e-mail com a evidência", TEAL if en else (190, 202, 198),
                size=14, press=press_mail)
    nav_bar(s, "Escanear")
    return s.img


PHOTO = None


def scr_email(attach=0.0, press_send=0.0, press_cam=0.0, hl=0.0):
    s = Screen(WHITE)
    rect(s.d, s.c, 0, 0, SWS, 96, (246, 247, 249))
    status_bar(s, light=False)
    text(s.d, s.c, 16, 72, "Novo e-mail", 17, TXT, True, "lm")
    off = 1.5 * press_send
    rect(s.d, s.c, 262, 58 + off, 344, 86 + off, mix(BLUE, (10, 40, 110), press_send * 0.6), r=14)
    text(s.d, s.c, 303, 72 + off, "Enviar", 13, WHITE, True, "mm")
    rect(s.d, s.c, 0, 96, SWS, 97, LINE)
    text(s.d, s.c, 16, 110, "Para:", 11, GREY)
    text(s.d, s.c, 56, 110, "Canal da região (Teams)", 11.5, TXT, True)
    rect(s.d, s.c, 16, 132, SWS - 16, 133, LINE)
    text(s.d, s.c, 16, 142, "Assunto:", 11, GREY)
    text(s.d, s.c, 16, 160, "DEVICE: Inventory Number|", 13, TXT, True)
    text(s.d, s.c, 16, 178, "012959|ALTO ARAGUAIA", 13, TXT, True)
    rect(s.d, s.c, 16, 202, SWS - 16, 203, LINE)
    body = [("EQUIPAMENTO", 1), ("Inventory Number: 012959", 0), ("Status: In Stock", 0), ("LOCAL", 1),
            ("Unidade: ALTO ARAGUAIA", 0), ("LOCALIZAÇÃO DO CELULAR", 1), ("Latitude, longitude, data", 0),
            ("RESPONSÁVEL PELA LEITURA", 1), ("Iza Silva", 0)]
    y = 216
    for ln, b in body:
        text(s.d, s.c, 16, y, ln, 11.5, TXT if b else (70, 80, 92), bool(b))
        y += 21
    text(s.d, s.c, 16, y + 6, "Anexe uma foto deste equipamento.", 11.5, TXT, True)
    if attach > 0:
        u = ease_out(attach)
        ay = 446 + (1 - u) * 30
        rect(s.d, s.c, 16, ay, SWS - 16, ay + 66, mix(WHITE, (247, 244, 240), u), r=10,
             outline=mix(WHITE, mix(LINE, GREEN, hl), u), w=1.4 + 1.4 * hl)
        if PHOTO is not None:
            ph = PHOTO.resize((int(84 * SK), int(50 * SK)), Image.LANCZOS)
            if u < 1:
                ph = Image.blend(Image.new("RGB", ph.size, WHITE), ph, u)
            s.img.paste(ph, (int(26 * SK), int((ay + 8) * SK)))
        text(s.d, s.c, 122, ay + 16, "foto_012959.jpg", 13, mix(WHITE, TXT, u), True)
        text(s.d, s.c, 122, ay + 38, "placa e nº de série", 11, mix(WHITE, GREY, u))
    rect(s.d, s.c, 0, SHS - 70, SWS, SHS - 69, LINE)
    yb = SHS - 42
    ell(s.d, s.c, 42, yb, 5, 9, None, TXT, 1.5)
    text(s.d, s.c, 56, yb, "Anexar", 13, TXT, False, "lm")
    if press_cam > 0:
        rect(s.d, s.c, 220, yb - 18, 330, yb + 18, mix(WHITE, (222, 230, 242), press_cam), r=18)
    rect(s.d, s.c, 232, yb - 8, 252, yb + 8, None, r=3, outline=TXT, w=1.5)
    ell(s.d, s.c, 242, yb, 4, 4, None, TXT, 1.3)
    text(s.d, s.c, 262, yb, "Câmera", 13, TXT, False, "lm")
    rect(s.d, s.c, 120, SHS - 12, 240, SHS - 8, (60, 60, 60), r=2)
    return s.img


def scr_photo(t, press=0.0, flash=0.0):
    s = Screen((0, 0, 0))
    status_bar(s)
    text(s.d, s.c, SWS / 2, 70, "FOTO", 13, (255, 186, 40), True, "mm")
    view_img, _ = camera_view(t, (int(SWS * SK), int(470 * SK)), flash)
    s.img.paste(view_img, (0, int(100 * SK)))
    s.d = ImageDraw.Draw(s.img)
    cy = 676
    ell(s.d, s.c, SWS / 2, cy, 34, 34, None, WHITE, 4)
    r = 27 - 4 * press
    ell(s.d, s.c, SWS / 2, cy, r, r, mix(WHITE, (200, 200, 200), press))
    rect(s.d, s.c, 40, cy - 20, 80, cy + 20, (60, 60, 60), r=8)
    return s.img


def scr_sent(u):
    s = Screen(WHITE)
    status_bar(s, light=False)
    k = ease_out(seg(u, 0.35, 0.75))
    if k > 0:
        r = 60 * k * (1 + 0.12 * math.sin(seg(u, 0.6, 0.9) * math.pi))
        ell(s.d, s.c, SWS / 2, 330, r, r, GREEN)
        if r > 10:
            check(s.d, s.c, SWS / 2, 330, r * 0.95, WHITE, 8 * k)
    a = ease(seg(u, 0.55, 0.9))
    text(s.d, s.c, SWS / 2, 410, "E-mail enviado", 21, mix(WHITE, GREEN, a), True, "mm")
    text(s.d, s.c, SWS / 2, 440, "Leitura contabilizada", 14, mix(WHITE, GREY, a), False, "mm")
    return s.img


def scr_records(hl=0.0):
    s = Screen()
    app_header(s, "Registros da Conferência")
    loc_card(s, 156)
    for i, (lab1, lab2, val) in enumerate((("E-mails", "Enviados", "1"), ("Total de", "Itens", "1"))):
        x0 = 12 + i * 172
        rect(s.d, s.c, x0, 214, x0 + 164, 266, WHITE, r=8, outline=LINE, w=1)
        text(s.d, s.c, x0 + 12, 226, lab1, 11, GREY)
        text(s.d, s.c, x0 + 12, 242, lab2, 11, GREY)
        text(s.d, s.c, x0 + 146, 240, val, 22, TXT, True, "rm")
    rect(s.d, s.c, 12, 278, SWS - 12, 312, WHITE, r=17, outline=LINE, w=1)
    ell(s.d, s.c, 32, 295, 6, 6, None, GREY, 1.4)
    text(s.d, s.c, 46, 295, "Buscar pela placa", 12, GREY, False, "lm")
    y = 326
    rect(s.d, s.c, 12, y, SWS - 12, y + 108, WHITE, r=10, outline=mix(LINE, GREEN, 0.6 + 0.4 * hl), w=1.6 + 1.6 * hl)
    text(s.d, s.c, 26, y + 12, "012959", 19, TXT, True)
    text(s.d, s.c, 26, y + 40, "ALTO ARAGUAIA", 11, GREY)
    text(s.d, s.c, 26, y + 56, "E-mail enviado ✓", 11, GREEN, True)
    rect(s.d, s.c, 26, y + 76, 112, y + 98, GREEN_L, r=6)
    text(s.d, s.c, 69, y + 87, "In Stock", 11, GREEN, True, "mm")
    rect(s.d, s.c, 238, y + 76, 334, y + 98, (234, 240, 238), r=6)
    text(s.d, s.c, 286, y + 87, "Abrir e-mail", 11, TXT, True, "mm")
    nav_bar(s, "Registros")
    return s.img


# ------------------------------------------------------------------ celular (mockup)
PH_X, PH_Y = 1300, 392          # centro do celular (design)
PH_SW, PH_SH = 322, 698         # tamanho da tela (design)
BEZ = 13
PHONE = None


def build_phone_frame():
    k = RS
    W_, H_ = int((PH_SW + 2 * BEZ) * k), int((PH_SH + 2 * BEZ) * k)
    pad = int(60 * k)
    shadow, sp = soft_shadow((W_, H_), int(58 * k), 22 * k, 95)
    frame = Image.new("RGBA", (W_ + 2 * pad, H_ + 2 * pad), (0, 0, 0, 0))
    frame.paste((20, 30, 40, 255), (pad - sp + int(4 * k), pad - sp + int(16 * k)), shadow)
    d = ImageDraw.Draw(frame)
    side = (50, 54, 60)
    d.rounded_rectangle([pad - 4 * k, pad + 150 * k, pad + 2 * k, pad + 200 * k], radius=2 * k, fill=side)
    d.rounded_rectangle([pad - 4 * k, pad + 215 * k, pad + 2 * k, pad + 265 * k], radius=2 * k, fill=side)
    d.rounded_rectangle([pad + W_ - 2 * k, pad + 190 * k, pad + W_ + 4 * k, pad + 270 * k], radius=2 * k, fill=side)
    d.rounded_rectangle([pad, pad, pad + W_, pad + H_], radius=int(56 * k), fill=(28, 30, 34))
    d.rounded_rectangle([pad + 2 * k, pad + 2 * k, pad + W_ - 2 * k, pad + H_ - 2 * k], radius=int(54 * k),
                        outline=(84, 88, 96), width=max(1, int(2 * k)))
    sx0, sy0 = pad + int(BEZ * k), pad + int(BEZ * k)
    sw, sh = int(PH_SW * k), int(PH_SH * k)
    mask = Image.new("L", (sw, sh), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, sw - 1, sh - 1], radius=int(44 * k), fill=255)
    island = (int(sw / 2 - 46 * k), int(10 * k), int(sw / 2 + 46 * k), int(34 * k))
    return frame, (sx0, sy0), mask, island


def paste_phone(img, screen):
    frame, (sx0, sy0), mask, island = PHONE
    fr = frame.copy()
    scr = screen.resize(mask.size, Image.LANCZOS)
    ImageDraw.Draw(scr).rounded_rectangle(island, radius=(island[3] - island[1]) / 2, fill=(8, 8, 10))
    fr.paste(scr, (sx0, sy0), mask)
    img.paste(fr, (int(PH_X * RS - fr.width / 2), int(PH_Y * RS - fr.height / 2)), fr)


def scr_to_design(sx, sy):
    return (PH_X - PH_SW / 2 + sx / SWS * PH_SW, PH_Y - PH_SH / 2 + sy / SHS * PH_SH)


def transition(a, b, u, kind="push"):
    if u <= 0:
        return a
    if u >= 1:
        return b
    u = ease(u)
    w, h = a.size
    if kind == "push":
        out = a.copy()
        off = int(w * u)
        out.paste(a.crop((off, 0, w, h)), (0, 0))
        out.paste(b.crop((0, 0, off, h)), (w - off, 0))
        return out
    if kind == "up":
        out = Image.blend(a, Image.new("RGB", a.size, (0, 0, 0)), 0.3 * u)
        off = int(h * (1 - u))
        if h - off > 0:
            out.paste(b.crop((0, 0, w, h - off)), (0, off))
        return out
    return Image.blend(a, b, u)


# ------------------------------------------------------------------ cenário (cartão à esquerda)
CARD = (56, 108, 1088, 694)     # x0, y0, x1, y1 (design)
ILL = None
STK = None
LABEL_N = (0.4875, 0.513)       # etiqueta 012959 na foto do estoque (normalizado)
LABEL_WN = (0.118, 0.092)


def view(src, cx, cy, zoom, size):
    sw, sh = src.size
    tw, th = size
    ar = tw / th
    vw = sw / zoom
    vh = vw / ar
    if vh > sh:
        vh = sh
        vw = vh * ar
    x0 = clamp(cx * sw - vw / 2, 0, max(0, sw - vw))
    y0 = clamp(cy * sh - vh / 2, 0, max(0, sh - vh))
    im = src.transform(size, Image.EXTENT, (x0, y0, x0 + vw, y0 + vh), Image.BICUBIC)
    return im, (x0 / sw, y0 / sh, vw / sw, vh / sh)


def card_scene(t):
    x0, y0, x1, y1 = CARD
    size = (int((x1 - x0) * RS), int((y1 - y0) * RS))
    if t < 9 or t >= 28.4:
        if t < 4:
            z, cx, cy = lerp(1.0, 1.05, t / 4), 0.5, 0.5
        elif t < 9:
            u = ease(seg(t, 4.2, 8.4))
            z, cx, cy = lerp(1.05, 1.85, u), lerp(0.5, 0.46, u), lerp(0.5, 0.56, u)
        else:
            z, cx, cy = lerp(1.1, 1.0, ease(seg(t, 28.4, 30))), 0.5, 0.5
        im, vp = view(ILL, cx, cy, z, size)
        if 8.6 <= t < 9:
            im2, vp = view(STK, 0.5, 0.5, 1.0, size)
            im = Image.blend(im, im2, ease(seg(t, 8.6, 9.0)))
    else:
        if t < 13:
            z, cx, cy = lerp(1.0, 1.08, seg(t, 9, 13)), 0.5, 0.5
        elif t < 19:
            u = ease(seg(t, 13.2, 15.6))
            z, cx, cy = lerp(1.08, 1.75, u), lerp(0.5, LABEL_N[0], u), lerp(0.5, LABEL_N[1], u)
        elif t < 25:
            z, cx, cy = lerp(1.75, 1.6, seg(t, 19, 25)), LABEL_N[0], LABEL_N[1]
        else:
            u = ease(seg(t, 25.2, 27.8))
            z, cx, cy = lerp(1.6, 1.0, u), lerp(LABEL_N[0], 0.5, u), lerp(LABEL_N[1], 0.5, u)
        im, vp = view(STK, cx, cy, z, size)
        if 28.0 <= t < 28.4:
            im2, _ = view(ILL, 0.5, 0.5, 1.1, size)
            im = Image.blend(im, im2, ease(seg(t, 28.0, 28.4)))
    vx, vy, vw, vh = vp

    def n2d(nx, ny):
        return (x0 + (nx - vx) / vw * (x1 - x0), y0 + (ny - vy) / vh * (y1 - y0))
    return im, n2d


def balloon(d, x, y, msg, u):
    """Balão de fala (x, y = ponta da cauda)."""
    if u <= 0:
        return
    s = 0.75 + 0.25 * ease_out(u)
    c = ID
    size = 28 * s
    tw = tlen(d, c, msg, size, True)
    w, h = tw + 52 * s, 66 * s
    bx0, by0 = x - 36 * s, y - h - 24 * s
    poly(d, c, [(x, y), (x + 2 * s, y - 28 * s), (x + 30 * s, y - 26 * s)], NAVY)
    rect(d, c, bx0, by0, bx0 + w, by0 + h, WHITE, r=20 * s, outline=NAVY, w=3)
    poly(d, c, [(x + 2.5 * s, y - 6 * s), (x + 5 * s, y - 28 * s), (x + 26 * s, y - 27 * s)], WHITE)
    text(d, c, bx0 + w / 2, by0 + h / 2, msg, size, TXT, True, "mm")


def chip(d, x, y, msg, u, fill=GREEN, fg=WHITE, size=24):
    if u <= 0:
        return
    a = ease_out(u)
    c = ID
    tw = tlen(d, c, msg, size, True)
    yy = y + (1 - a) * 14
    rect(d, c, x - tw / 2 - 22, yy - 24, x + tw / 2 + 22, yy + 24, mix(WHITE, fill, a), r=24,
         outline=(215, 222, 226) if fill == WHITE else None, w=1.5)
    text(d, c, x, yy, msg, size, mix(WHITE, fg, a), True, "mm")


# ------------------------------------------------------------------ indicador de toque
TAP_TIMES = [10.0, 13.3, 19.5, 20.5, 22.3, 23.3, 25.5]
DRAG = (5.0, 5.6)
TOUCH_PATH = [
    (4.4, (250, 420), 0), (4.95, (290, 185), 1), (5.65, (316, 185), 1), (6.2, (300, 300), 0),
    (9.3, (240, 700), 0), (9.85, (180, 583), 1), (10.4, (180, 583), 1), (10.8, (220, 690), 0),
    (12.6, (230, 560), 0), (13.15, (180, 432), 1), (13.6, (180, 432), 1), (14.0, (220, 560), 0),
    (19.0, (200, 560), 0), (19.35, (90, 346), 1), (19.9, (90, 346), 1), (20.35, (180, 485), 1),
    (20.8, (180, 485), 1), (21.2, (230, 600), 0),
    (21.9, (300, 640), 0), (22.15, (270, 738), 1), (22.55, (270, 738), 1), (23.15, (180, 676), 1),
    (23.6, (180, 676), 1), (24.0, (230, 600), 0),
    (25.0, (260, 240), 0), (25.4, (303, 72), 1), (25.8, (303, 72), 1), (26.1, (330, 200), 0),
]


def touch_state(t):
    pos, vis = None, 0.0
    for (ta, pa, va), (tb, pb, vb) in zip(TOUCH_PATH, TOUCH_PATH[1:]):
        if ta <= t <= tb:
            u = ease(seg(t, ta, tb))
            pos, vis = lerp2(pa, pb, u), lerp(va, vb, u)
            break
    if pos is None:
        return None, 0, 0, 0
    press = 1.0 if DRAG[0] <= t <= DRAG[1] else 0.0
    rip = 0.0
    for tp in TAP_TIMES + [DRAG[0]]:
        press = max(press, clamp(1 - abs(t - tp) / 0.12)) if tp != DRAG[0] else press
        if tp <= t < tp + 0.45:
            rip = seg(t, tp, tp + 0.45)
    return scr_to_design(*pos), vis, press, rip


def draw_touch(img, pos, vis, press, rip):
    over = Image.new("RGBA", img.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    x, y = pos[0] * RS, pos[1] * RS
    r = (22 - 5 * press) * RS
    d.ellipse([x - r - 4, y - r - 2, x + r + 4, y + r + 6], fill=(20, 30, 40, int(40 * vis)))
    d.ellipse([x - r, y - r, x + r, y + r], fill=(255, 255, 255, int(160 * vis)),
              outline=(70, 80, 90, int(130 * vis)), width=max(1, int(2 * RS)))
    if 0 < rip < 1:
        rr = (24 + 44 * ease_out(rip)) * RS
        d.ellipse([x - rr, y - rr, x + rr, y + rr], outline=(255, 255, 255, int(235 * (1 - rip))),
                  width=max(1, int(4 * RS * (1 - rip)) + 1))
    base = img.convert("RGBA")
    base.alpha_composite(over)
    return base.convert("RGB")


# ------------------------------------------------------------------ tela do celular no tempo t
_SC = {}


def C(key, fn):
    if key not in _SC:
        if len(_SC) > 300:
            _SC.clear()
        _SC[key] = fn()
    return _SC[key]


def tapv(t, t0, dd=0.13):
    return q(clamp(1 - abs(t - t0) / dd), 8)


def phone_screen(t):
    if t < 9:
        gps = q(ease(seg(t, 5.0, 5.6)))
        valid = q(seg(t, 6.6, 7.4))
        return C(("home", gps, valid, 0), lambda: scr_home(gps, valid))
    if t < 13:
        if t < 10.2:
            pr = tapv(t, 10.0)
            return C(("home", 1, 1, pr), lambda: scr_home(1, 1, pr))
        a = C(("home", 1, 1, 0), lambda: scr_home(1, 1, 0))
        b = C(("scan", 0), lambda: scr_scan(0))
        return transition(a, b, seg(t, 10.2, 10.6), "push")
    if t < 19:
        if t < 13.5:
            pr = tapv(t, 13.3)
            return C(("scan", pr), lambda: scr_scan(pr))
        succ = ease(seg(t, 16.3, 16.6))
        su = None if t < 14.0 else (math.sin((t - 14.0) * 3.2 - math.pi / 2) + 1) / 2
        rd = scr_reading(t, su, succ)
        if t < 13.8:
            return transition(C(("scan", 0), lambda: scr_scan(0)), rd, seg(t, 13.5, 13.8), "fade")
        if t >= 17.6:
            pl = C(("plate", 0, 0, 0), lambda: scr_plate(0))
            return transition(rd, pl, seg(t, 17.6, 18.0), "push")
        return rd
    if t < 22:
        if t < 20.7:
            ins = 1.0 if t >= 19.55 else 0.0
            pi_, pm = tapv(t, 19.5), tapv(t, 20.5)
            return C(("plate", ins, pi_, pm), lambda: scr_plate(ins, pi_, pm))
        a = C(("plate", 1, 0, 0), lambda: scr_plate(1))
        b = C(("mail", 0, 0, 0, 0), lambda: scr_email())
        return transition(a, b, seg(t, 20.7, 21.1), "up")
    if t < 25:
        if t < 22.5:
            pc = tapv(t, 22.3)
            return C(("mail", 0, 0, pc, 0), lambda: scr_email(0, 0, pc))
        fl = clamp(1 - abs(t - 23.4) / 0.15)
        ph = scr_photo(t, tapv(t, 23.3), fl)
        if t < 22.8:
            return transition(C(("mail", 0, 0, 0, 0), lambda: scr_email()), ph, seg(t, 22.5, 22.8), "fade")
        if t < 23.8:
            return ph
        att = q(seg(t, 24.1, 24.6))
        hl = q(clamp(math.sin(seg(t, 24.4, 25.0) * math.pi)), 8)
        m = C(("mail", att, 0, 0, hl), lambda: scr_email(att, 0, 0, hl))
        return transition(ph, m, seg(t, 23.8, 24.1), "fade")
    if t < 28:
        if t < 25.7:
            ps = tapv(t, 25.5)
            return C(("mail", 1, ps, 0, 0), lambda: scr_email(1, ps))
        u = q(seg(t, 25.7, 27.0), 30)
        sent = C(("sent", u), lambda: scr_sent(u))
        if t < 25.95:
            return transition(C(("mail", 1, 0, 0, 0), lambda: scr_email(1)), sent, seg(t, 25.7, 25.95), "fade")
        return sent
    hl = q(clamp(math.sin(seg(t, 28.5, 29.5) * math.pi)), 8)
    rec = C(("rec", hl), lambda: scr_records(hl))
    if t < 28.4:
        return transition(C(("sent", 1.0), lambda: scr_sent(1.0)), rec, seg(t, 28.0, 28.4), "push")
    return rec


# ------------------------------------------------------------------ faixa de instrução
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


def draw_strip(img, t):
    c = ID
    y0 = H - STRIP
    img.paste(STRIP_SHADOW, (0, int((y0 - 24) * RS)), STRIP_SHADOW)
    d = ImageDraw.Draw(img)
    rect(d, c, 0, y0, W, H, WHITE)
    rect(d, c, 0, y0, 8, H, TEAL)
    idx = max(i for i, s in enumerate(STEPS) if t >= s[0])
    a, b, msg = STEPS[idx]
    u = ease(seg(t, a, a + 0.4))
    cy = y0 + STRIP / 2
    ell(d, c, 84, cy, 34, 34, NAVY)
    text(d, c, 84, cy, str(idx + 1), 32, WHITE, True, "mm")
    text(d, c, 142 + (1 - u) * 24, cy, msg, 40, mix(WHITE, TXT, u), True, "lm")
    text(d, c, W - 56, cy - 16, f"Passo {idx + 1} de 8", 22, (96, 106, 116), True, "rm")
    for i in range(8):
        ell(d, c, W - 56 - (7 - i) * 24, cy + 18, 6.5, 6.5, TEAL if i <= idx else (214, 219, 223))
    rect(d, c, 0, y0, W * t / DUR, y0 + 5, TEAL)


# ------------------------------------------------------------------ quadro
BG_IMG = None
CARD_SHADOW = None
STRIP_SHADOW = None


def build_static():
    global BG_IMG, CARD_SHADOW, STRIP_SHADOW, PHONE, ILL, STK, PHOTO
    ILL = Image.open(os.path.join(ASSETS, "ilustracao.png")).convert("RGB")
    STK = Image.open(os.path.join(ASSETS, "estoque.png")).convert("RGB")

    def up(im):
        return im.resize((im.width * 4, im.height * 4), Image.LANCZOS).filter(
            ImageFilter.UnsharpMask(radius=3, percent=60, threshold=2))
    ILL, STK = up(ILL), up(STK)
    bg = Image.new("RGB", (RW, RH), BG1)
    d = ImageDraw.Draw(bg)
    for i in range(RH):
        d.line([(0, i), (RW, i)], fill=mix(BG1, BG2, i / RH))
    blob = Image.new("L", (RW, RH), 0)
    bd = ImageDraw.Draw(blob)
    bd.ellipse([RW * 0.62, -RH * 0.25, RW * 1.15, RH * 0.6], fill=120)
    bd.ellipse([-RW * 0.15, RH * 0.55, RW * 0.35, RH * 1.2], fill=90)
    blob = blob.filter(ImageFilter.GaussianBlur(80))
    BG_IMG = Image.composite(Image.new("RGB", (RW, RH), (214, 232, 228)), bg, blob)
    x0, y0, x1, y1 = CARD
    CARD_SHADOW = soft_shadow((int((x1 - x0) * RS), int((y1 - y0) * RS)), int(22 * RS), 18 * RS, 70)
    ss = Image.new("L", (RW, int(24 * RS)), 0)
    sd = ImageDraw.Draw(ss)
    for i in range(ss.height):
        sd.line([(0, i), (RW, i)], fill=int(45 * (i / ss.height) ** 2))
    STRIP_SHADOW = Image.merge("RGBA", [Image.new("L", ss.size, 30)] * 3 + [ss])
    PHONE = build_phone_frame()
    view_img, lab = camera_view(0.0, (720, 1560))
    (lx, ly, lw, lh), _ = lab
    k = 720 / 360
    cx, cy = (lx + lw / 2) * k, (ly + lh / 2) * k
    PHOTO = view_img.crop((int(cx - 260), int(cy - 155), int(cx + 260), int(cy + 155)))


def render(t):
    img = BG_IMG.copy()
    x0, y0, x1, y1 = CARD
    sh, pad = CARD_SHADOW
    img.paste((20, 40, 50), (int(x0 * RS) - pad, int(y0 * RS) - pad + int(10 * RS)), sh)
    scene, n2d = card_scene(t)
    fl = clamp(1 - abs(t - 23.4) / 0.2)
    if fl > 0:
        scene = Image.blend(scene, Image.new("RGB", scene.size, WHITE), 0.75 * fl)
    mask = Image.new("L", scene.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, scene.width - 1, scene.height - 1], radius=int(22 * RS), fill=255)
    img.paste(scene, (int(x0 * RS), int(y0 * RS)), mask)
    d = ImageDraw.Draw(img)
    # etiqueta do cartão
    rect(d, ID, x0 + 20, y0 + 20, x0 + 330, y0 + 64, WHITE, r=22, outline=(220, 226, 230), w=1.2)
    ell(d, ID, x0 + 44, y0 + 42, 7, 7, GREEN if 5.6 <= t else (180, 186, 192))
    text(d, ID, x0 + 60, y0 + 42, "Estoque de TI · Alto Araguaia", 16, TXT, True, "lm")
    # sobreposições
    if t < 4:
        hx, hy = n2d(0.40, 0.18)
        balloon(d, hx, hy, "Oi! Vamos fazer uma leitura?", seg(t, 0.5, 0.9))
    if t >= 28.4:
        hx, hy = n2d(0.40, 0.18)
        balloon(d, hx, hy, "Pronto! Leitura enviada ✓", seg(t, 28.6, 29.0))
    if 5.6 <= t < 8.6:
        chip(d, x1 - 200, y1 - 120, "GPS ativado ✓", seg(t, 5.6, 5.9), GREEN)
        if t >= 6.8:
            chip(d, x1 - 260, y1 - 56, "ALTO ARAGUAIA · Localização validada", seg(t, 6.8, 7.1), WHITE, GREEN, 20)
    if 13.6 <= t < 25.2:
        lx, ly = n2d(LABEL_N[0] - LABEL_WN[0] / 2, LABEL_N[1] - LABEL_WN[1] / 2)
        lx2, ly2 = n2d(LABEL_N[0] + LABEL_WN[0] / 2, LABEL_N[1] + LABEL_WN[1] / 2)
        succ = ease(seg(t, 16.3, 16.6))
        if succ <= 0 and t >= 14.0:
            su = (math.sin((t - 14.0) * 3.2 - math.pi / 2) + 1) / 2
            yy = lerp(ly, ly2, su)
            rect(d, ID, lx - 10, yy - 2.5, lx2 + 10, yy + 2.5, (70, 240, 150))
        col = mix((240, 242, 244), (50, 200, 100), succ)
        a = ease(seg(t, 13.6, 14.0))
        if a > 0:
            rect(d, ID, lx - 8, ly - 8, lx2 + 8, ly2 + 8, None, r=8, outline=col, w=3 + 3 * succ)
        if succ > 0:
            chip(d, (lx + lx2) / 2, ly - 48, "Placa 012959 ✓", succ, GREEN, WHITE, 26)
    if 24.2 <= t < 25.4:
        chip(d, (x0 + x1) / 2, y1 - 50, "Foto anexada: foto_012959.jpg", seg(t, 24.2, 24.5), WHITE, TXT, 22)
    if 26.4 <= t < 28.0:
        chip(d, (x0 + x1) / 2, y1 - 50, "E-mail enviado · Leitura contabilizada", seg(t, 26.4, 26.7), GREEN, WHITE, 22)
    paste_phone(img, phone_screen(t))
    # aviãozinho
    pu = seg(t, 25.7, 26.8)
    if 0 < pu < 1:
        d = ImageDraw.Draw(img)
        sx, sy = scr_to_design(303, 72)
        ex, ey = 1660, -80
        cx1, cy1 = sx - 200, sy - 30
        pts = []
        for kk in range(25):
            v = ease_out(pu) * kk / 24
            pts.append(((1 - v) ** 2 * sx + 2 * (1 - v) * v * cx1 + v * v * ex,
                        (1 - v) ** 2 * sy + 2 * (1 - v) * v * cy1 + v * v * ey))
        for kk in range(0, len(pts) - 2, 3):
            line(d, ID, [pts[kk], pts[kk + 1]], (150, 190, 180), 3)
        bx, by = pts[-1]
        ang = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0] + 1e-6)
        s = 34
        ca, sa = math.cos(ang), math.sin(ang)

        def R(px_, py_):
            return (bx + px_ * ca - py_ * sa, by + px_ * sa + py_ * ca)
        poly(d, ID, [R(s, 0), R(-s * 0.7, -s * 0.6), R(-s * 0.3, 0)], TEAL)
        poly(d, ID, [R(s, 0), R(-s * 0.3, 0), R(-s * 0.7, s * 0.45)], TEAL_D)
    pos, vis, press, rip = touch_state(t)
    if pos is not None and vis > 0.01:
        img = draw_touch(img, pos, vis, press, rip)
    draw_strip(img, t)
    return img


def main():
    build_static()
    mp4 = os.path.join(HERE, "leitura-equipamento.mp4")
    gif = os.path.join(HERE, "leitura-equipamento.gif")
    n = int(DUR * FPS)
    fade = int(0.5 * FPS)
    first = None
    proc = subprocess.Popen(
        ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "1280x720",
         "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
         "-preset", "slow", "-movflags", "+faststart", mp4], stdin=subprocess.PIPE)
    for i in range(n):
        t = i / FPS
        fr = render(t).resize((1280, 720), Image.LANCZOS)
        if i == 0:
            first = fr
        if i >= n - fade:
            fr = Image.blend(fr, first, (i - (n - fade) + 1) / (fade + 1))
        proc.stdin.write(fr.tobytes())
        if i % 96 == 0:
            print(f"{t:5.1f}s", flush=True)
    proc.stdin.close()
    proc.wait()
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", mp4, "-vf",
         "fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=128:stats_mode=full[p];"
         "[b][p]paletteuse=dither=bayer:bayer_scale=5",
         "-loop", "0", gif], check=True)
    print("ok:", mp4, gif)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        build_static()
        times = [float(v) for v in sys.argv[3:]]
        thumbs = [render(t).resize((800, 450), Image.LANCZOS) for t in times]
        cols = 2
        rows = (len(thumbs) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 800, rows * 450), WHITE)
        for k, th in enumerate(thumbs):
            sheet.paste(th, ((k % cols) * 800, (k // cols) * 450))
        sheet.save(sys.argv[2])
    else:
        main()
