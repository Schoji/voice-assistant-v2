import math
import random
import time

from .oled import W, font

STATES = ("idle", "listen", "think", "talk", "sleep", "error")
BAND = 16
EYES_X, EYE_Y = (42, 86), 36
MOUTH_X, MOUTH_Y = 64, 55


class Face:
    def __init__(self):
        self.small = font(11)
        self.zfonts = (font(8), font(10), font(13))
        self.next_blink = time.time() + 2
        self.blink_until = 0
        self.look = 0
        self.next_look = time.time() + 3

    def eyes(self, d, now, w=18, h=20, dx=0, dy=0):
        if now > self.next_blink:
            self.blink_until = now + 0.15
            self.next_blink = now + random.uniform(2, 5)
        if now < self.blink_until:
            h = 2
        for x in EYES_X:
            cx, cy = x + dx, EYE_Y + dy
            d.rounded_rectangle((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
                                radius=min(w, h) // 3, fill=1)

    def band_text(self, d, now, text):
        tw = d.textlength(text, font=self.small)
        if tw <= W:
            x = (W - tw) / 2
        else:
            x = W - (now * 40) % (tw + W)
        d.text((x, 1), text, font=self.small, fill=1)

    def idle(self, d, now, text):
        if now > self.next_look:
            self.look = random.choice((-6, 0, 0, 6))
            self.next_look = now + random.uniform(2, 4)
        self.eyes(d, now, dx=self.look)
        d.arc((MOUTH_X - 10, MOUTH_Y - 7, MOUTH_X + 10, MOUTH_Y + 3), 20, 160, fill=1, width=2)

    def talk(self, d, now, text):
        self.eyes(d, now)
        o = random.Random(int(now * 8)).randint(1, 5)
        d.ellipse((MOUTH_X - 8, MOUTH_Y - o, MOUTH_X + 8, MOUTH_Y + o), fill=1)
        self.band_text(d, now, text or "...")

    def think(self, d, now, text):
        self.eyes(d, now, h=14, dx=6, dy=-4)
        d.line((MOUTH_X - 6, MOUTH_Y + 1, MOUTH_X + 8, MOUTH_Y - 1), fill=1, width=2)
        self.band_text(d, now, (text or "myślę") + "." * (int(now * 2) % 4))

    def listen(self, d, now, text):
        self.eyes(d, now, w=20, h=24)
        d.ellipse((MOUTH_X - 3, MOUTH_Y - 3, MOUTH_X + 3, MOUTH_Y + 3), outline=1, width=2)
        for i in range(16):
            lvl = abs(math.sin(now * 5 + i * 1.3) * math.sin(now * 1.5 + i * 0.4))
            bh = 1 + int(lvl * 13)
            x = 33 + i * 4
            d.rectangle((x, BAND - 2 - bh, x + 1, BAND - 2), fill=1)

    def sleep(self, d, now, text):
        for x in EYES_X:
            d.arc((x - 9, EYE_Y - 8, x + 9, EYE_Y + 4), 20, 160, fill=1, width=2)
        r = 2 + (math.sin(now * 2) + 1)
        d.ellipse((MOUTH_X - r, MOUTH_Y - r, MOUTH_X + r, MOUTH_Y + r), outline=1, width=1)
        for i in range(int(now * 2) % 4):
            d.text((78 + i * 12, 6 - i * 3), "zZZ"[i], font=self.zfonts[i], fill=1)

    def error(self, d, now, text):
        dx = random.Random(int(now * 6)).choice((0, 0, 0, -2, 2))
        for x in EYES_X:
            cx = x + dx
            d.line((cx - 7, EYE_Y - 7, cx + 7, EYE_Y + 7), fill=1, width=3)
            d.line((cx - 7, EYE_Y + 7, cx + 7, EYE_Y - 7), fill=1, width=3)
        d.arc((MOUTH_X - 10 + dx, MOUTH_Y - 1, MOUTH_X + 10 + dx, MOUTH_Y + 9), 200, 340, fill=1, width=2)
        if text or now % 1 < 0.75:
            self.band_text(d, now, text or "błąd")