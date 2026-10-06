"""Draws one frame: the beat's View, animated from the previous View at progress t (0..1)."""
import math

import pygame

from script import rname

W, H = 1280, 720

BG = (15, 23, 42)
PANEL = (30, 41, 59)
CELL = (39, 52, 73)
LINE = (71, 85, 105)
TEXT = (226, 232, 240)
MUTED = (148, 163, 184)
GREEN = (34, 197, 94)
RED = (239, 68, 68)
AMBER = (245, 158, 11)
BLUE = (59, 130, 246)
PURPLE = (168, 85, 247)
GROUP = {"alloc": (56, 189, 248), "max": (244, 114, 182), "need": (250, 204, 21),
         "avail": (52, 211, 153), "work": (129, 140, 248), "req": (251, 146, 60)}
CELL_HL = {"ok": GREEN, "bad": RED, "focus": BLUE}
ROW_HL = {"active": (113, 90, 20), "done": (30, 35, 45), "stuck": (110, 30, 30), "trial": (80, 45, 120)}
BANNER = {"ok": GREEN, "bad": RED, "wait": AMBER, "info": BLUE}


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def ease(x):
    x = clamp(x)
    return x * x * (3 - 2 * x)


def win(t, w):
    return ease((t - w[0]) / max(1e-6, w[1] - w[0]))


def mix(c1, c2, k):
    return tuple(int(a + (b - a) * k) for a, b in zip(c1, c2))


class Renderer:
    def __init__(self, surface):
        self.s = surface
        pygame.font.init()
        names = "dejavusans,segoeui,arial,helvetica,liberationsans"
        self.f = {sz: pygame.font.SysFont(names, sz) for sz in (16, 18, 22, 24, 28)}
        self.fb = {sz: pygame.font.SysFont(names, sz, bold=True) for sz in (16, 18, 20, 22, 26, 30, 44, 60, 84)}
        self.le = "≤" if self._has(self.fb[22], "≤") else "<="
        self.gt = ">"
        self.arrow = "→" if self._has(self.fb[22], "→") else "->"

    @staticmethod
    def _has(font, ch):
        m = font.metrics(ch)
        return bool(m) and m[0] is not None

    # ---------- small helpers ----------
    def text(self, txt, font, color, pos, anchor="center", alpha=255):
        img = font.render(str(txt), True, color)
        if alpha < 255:
            img.set_alpha(int(alpha))
        r = img.get_rect(**{anchor: pos})
        self.s.blit(img, r)
        return r

    def rect(self, color, r, radius=8, width=0, alpha=255):
        if alpha >= 255:
            pygame.draw.rect(self.s, color, r, width, border_radius=radius)
        else:
            tmp = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(tmp, (*color, int(alpha)), tmp.get_rect(), width, border_radius=radius)
            self.s.blit(tmp, r.topleft)

    def wrap(self, txt, font, width):
        lines, cur = [], ""
        for word in txt.split(" "):
            test = (cur + " " + word).strip()
            if font.size(test)[0] <= width:
                cur = test
            else:
                lines.append(cur)
                cur = word
        lines.append(cur)
        return lines

    # ---------- layout ----------
    def layout(self, v):
        n, m = v.n, v.m
        L = {}
        x0, y0 = 40, 92
        name_w, fin_w, gap = 64, 76, 16
        cw = int(min(62, (830 - name_w - fin_w - 3 * gap) / (3 * m)))
        cw = max(cw, -(-110 // m))  # keep group titles from overlapping when m is small
        rh = int(min(54, (560 - y0 - 58) / n))
        L["cw"], L["rh"] = cw, rh
        L["head_y"] = y0
        gx = x0 + name_w
        L["groups"] = {}
        for g in ("alloc", "max", "need"):
            L["groups"][g] = pygame.Rect(gx, y0, cw * m, 58 + rh * n)
            for i in range(n):
                for j in range(m):
                    L[(g, i, j)] = pygame.Rect(gx + j * cw + 2, y0 + 58 + i * rh + 2, cw - 4, rh - 4)
            gx += cw * m + gap
        L["finish_x"] = gx
        L["fin_w"] = fin_w
        L["table"] = pygame.Rect(x0, y0, gx + fin_w - x0, 58 + rh * n)
        for i in range(n):
            L[("row", i)] = pygame.Rect(x0 - 6, y0 + 58 + i * rh, gx + fin_w - x0 + 12, rh)
            L[("name", i)] = (x0 + name_w // 2, y0 + 58 + i * rh + rh // 2)
        # right panel
        px = 905
        bw = int(min(58, 320 / m - 6))
        for k, y in (("avail", 120), ("work", 220), ("req", 320)):
            for j in range(m):
                L[(k, j)] = pygame.Rect(px + j * (bw + 6), y, bw, 46)
            L[(k, "label")] = (px, y - 24)
        L["cmp"] = pygame.Rect(px - 10, 395, 345, 100)
        L["seq"] = pygame.Rect(px - 10, 505, 345, 80)
        return L

    def cell_center(self, L, key):
        return L[key].center

    # ---------- frame ----------
    def draw(self, beat, prev, t, info):
        """info: dict(chapter, progress, chapters[(frac, name)], caption_k, paused, speed, sample)"""
        v = beat.view
        p = prev if prev is not None else v
        fx = {e[0]: e for e in beat.effects}
        self.s.fill(BG)

        # title card replaces the whole stage
        if v.title is not None:
            a = 1.0 if p.title is not None else win(t, (0, 0.3))
            self.draw_title(v.title, a)
            self.draw_caption(beat.caption, info)
            self.draw_progress(info)
            return

        L = self.layout(v)
        num_win = {}
        if "fly" in fx:
            for k in fx["fly"][2]:
                num_win[k] = (0.45, 0.85)
        stag = fx["stagger"][1] if "stagger" in fx else {}

        def num(key, cur, old):
            if old is None or old == cur:
                return cur
            return round(old + (cur - old) * win(t, num_win.get(key, (0.15, 0.8))))

        def hl_color(key, base):
            w = stag.get(key, (0.0, 0.3))
            c_new = CELL_HL.get(v.cell_hl.get(key), base)
            c_old = CELL_HL.get(p.cell_hl.get(key), base)
            return mix(c_old, c_new, win(t, w))

        self.draw_header(info)
        rows_shown = p.rows_shown + (v.rows_shown - p.rows_shown) * win(t, (0, 0.9))

        # column-group highlight
        for g, r in L["groups"].items():
            k = (1 if g in v.col_hl else 0) * win(t, (0, 0.4)) + (1 if g in p.col_hl else 0) * (1 - win(t, (0, 0.4)))
            if k > 0.01:
                self.rect(GROUP[g], r.inflate(10, 10), 10, alpha=40 * k)
                self.rect(GROUP[g], r.inflate(10, 10), 10, width=2, alpha=255 * k)

        # headers
        hy = L["head_y"]
        self.text("Process", self.fb[16], MUTED, (L[("name", 0)][0], hy + 40))
        for g, label in (("alloc", "Allocation"), ("max", "Max"), ("need", "Need")):
            r = L["groups"][g]
            self.text(label, self.fb[20], GROUP[g], (r.centerx, hy + 14))
            for j in range(v.m):
                self.text(rname(j), self.fb[16], MUTED, (r.x + j * L["cw"] + L["cw"] // 2, hy + 42))
        self.text("Finish", self.fb[16], MUTED, (L["finish_x"] + L["fin_w"] // 2, hy + 40))

        # rows
        for i in range(v.n):
            a = clamp(rows_shown - i)
            if a <= 0:
                continue
            off = int((1 - ease(a)) * 40)
            rr = L[("row", i)].move(off, 0)
            c_old = ROW_HL.get(p.row_hl.get(i))
            c_new = ROW_HL.get(v.row_hl.get(i))
            k = win(t, (0, 0.3))
            if c_old or c_new:
                c = mix(c_old or BG, c_new or BG, k)
                self.rect(c, rr, 10, alpha=255 * a)
            done = v.row_hl.get(i) == "done"
            name_col = MUTED if done else TEXT
            self.text(f"P{i}", self.fb[22], name_col, (L[("name", i)][0] + off, L[("name", i)][1]), alpha=255 * a)
            for g in ("alloc", "max", "need"):
                vals_new = getattr(v, g)[i]
                vals_old = getattr(p, g)[i]
                if g == "need":
                    na = (p.need_shown[i] + (v.need_shown[i] - p.need_shown[i]) *
                          win(t, self._need_window(fx, i))) * a
                else:
                    na = a
                for j in range(v.m):
                    key = (g, i, j)
                    r = L[key].move(off, 0)
                    self.rect(hl_color(key, CELL), r, 6, alpha=255 * a)
                    if na > 0:
                        self.text(num(key, vals_new[j], vals_old[j]), self.fb[22],
                                  MUTED if done else TEXT, r.center, alpha=255 * na)
            # finish column
            fc = (L["finish_x"] + L["fin_w"] // 2 + off, L[("name", i)][1])
            if v.finish is not None:
                fin = v.finish[i]
                was = p.finish[i] if p.finish is not None else False
                if fin:
                    k2 = 1 if was else win(t, (0.6, 0.9))
                    self.text("true", self.fb[18], mix(MUTED, GREEN, k2), fc, alpha=255 * a)
                else:
                    self.text("false", self.f[18], RED if v.row_hl.get(i) == "stuck" else MUTED, fc, alpha=255 * a)

        # right panel boxes
        self.draw_vector(L, "avail", "Available", v.available, p.available, num, hl_color, 1.0)
        if v.work is not None or p.work is not None:
            if v.work is not None:
                a = 1.0 if p.work is not None else win(t, (0, 0.3))
                self.draw_vector(L, "work", "Work", v.work, p.work if p.work is not None else [0] * v.m,
                                 num, hl_color, a)
            else:
                self.draw_vector(L, "work", "Work", p.work, p.work, num, hl_color, 1 - win(t, (0, 0.3)))
        if v.request is not None:
            a = 1.0 if p.request is not None else win(t, (0, 0.3))
            self.draw_vector(L, "req", f"Request from P{v.req_pid}", v.request, v.request, num, hl_color, a)
        elif p.request is not None:
            self.draw_vector(L, "req", f"Request from P{p.req_pid}", p.request, p.request, num, hl_color,
                             1 - win(t, (0, 0.3)))

        if v.compare is not None:
            self.draw_compare(L, v.compare, stag, t, 1.0 if p.compare == v.compare else win(t, (0, 0.2)))
        self.draw_sequence(L, v, p, t)

        if "fly" in fx:
            self.draw_fly(L, fx["fly"], p, t)

        if v.banner is not None:
            popped = "pop" in fx and p.banner != v.banner
            self.draw_banner(L, v.banner, win(t, (0, 0.25)) if popped else 1.0, t if popped else 1.0)
        elif p.banner is not None:
            self.draw_banner(L, p.banner, 1 - win(t, (0, 0.2)), 1.0)

        self.draw_caption(beat.caption, info)
        self.draw_progress(info)

    def _need_window(self, fx, i):
        if "stagger_rows" in fx:
            d = fx["stagger_rows"][1]
            return (0.1 + 0.08 * (i - d), 0.3 + 0.08 * (i - d))
        return (0.2, 0.6)

    # ---------- parts ----------
    def draw_header(self, info):
        self.rect(PANEL, pygame.Rect(0, 0, W, 60), 0)
        self.text(info["chapter"], self.fb[26], TEXT, (32, 30), "midleft")
        self.text(info["sample"], self.f[18], MUTED, (W - 32, 30), "midright")

    def draw_vector(self, L, k, label, vals, old, num, hl_color, alpha):
        if alpha <= 0.01:
            return
        self.text(label, self.fb[20], GROUP[k], L[(k, "label")], "topleft", alpha=255 * alpha)
        for j, val in enumerate(vals):
            r = L[(k, j)]
            self.rect(hl_color((k, j), CELL), r, 8, alpha=255 * alpha)
            self.rect(GROUP[k], r, 8, width=2, alpha=255 * alpha)
            self.text(num((k, j), val, old[j] if old is not None else None), self.fb[26], TEXT, r.center,
                      alpha=255 * alpha)
            self.text(rname(j), self.f[16], MUTED, (r.centerx, r.bottom + 10), alpha=200 * alpha)

    def draw_compare(self, L, cmp, stag, t, alpha):
        left_l, left, right_l, right = cmp
        box = L["cmp"]
        self.rect(PANEL, box, 12, alpha=255 * alpha)
        self.text("Compare each resource", self.f[16], MUTED, (box.x + 12, box.y + 8), "topleft", alpha=255 * alpha)
        m = len(left)
        colw = min(48, (box.w - 120) // m)
        x0 = box.x + 112
        self.text(left_l, self.fb[16], TEXT, (box.x + 12, box.y + 42), "midleft", alpha=255 * alpha)
        self.text(right_l, self.fb[16], TEXT, (box.x + 12, box.y + 82), "midleft", alpha=255 * alpha)
        windows = list(stag.values())
        for j in range(m):
            cx = x0 + j * colw + colw // 2
            w = (0.1 + 0.55 * j / m, 0.1 + 0.55 * (j + 1) / m)
            k = win(t, w) if windows else 1
            ok = left[j] <= right[j]
            col = mix(TEXT, GREEN if ok else RED, k)
            self.text(left[j], self.fb[22], col, (cx, box.y + 42), alpha=255 * alpha)
            self.text(right[j], self.fb[22], col, (cx, box.y + 82), alpha=255 * alpha)
            if k > 0:
                self.text(self.le if ok else self.gt, self.fb[20], col, (cx, box.y + 62), alpha=255 * alpha * k)

    def draw_sequence(self, L, v, p, t):
        box = L["seq"]
        if v.finish is None:
            return
        self.text("Safe sequence", self.fb[20], GREEN, (box.x + 10, box.y - 6), "topleft")
        x, y = box.x + 10, box.y + 24
        for idx, pid in enumerate(v.sequence):
            new = idx >= len(p.sequence)
            a = win(t, (0.55, 0.9)) if new else 1
            chip = pygame.Rect(x, y, 50, 32)
            if chip.right > box.right:
                x, y = box.x + 10, y + 40
                chip = pygame.Rect(x, y, 50, 32)
            chip = chip.move(0, int((1 - a) * -20))
            self.rect(GREEN, chip, 16, alpha=200 * a)
            self.text(f"P{pid}", self.fb[18], BG, chip.center, alpha=255 * a)
            x += 58

    def draw_fly(self, L, fx, p, t):
        _, srcs, dsts = fx
        k = win(t, (0.05, 0.55))
        if k <= 0 or k >= 1:
            return
        for s, d in zip(srcs, dsts):
            val = self._value(p, s)
            a, b = pygame.Vector2(L[s].center), pygame.Vector2(L[d].center)
            pos = a.lerp(b, k)
            pos.y -= math.sin(k * math.pi) * 60  # arc
            col = GROUP.get(s[0], AMBER)
            r = pygame.Rect(0, 0, 40, 34)
            r.center = (int(pos.x), int(pos.y))
            self.rect(col, r, 17)
            self.text(f"+{val}" if d[0] in ("work", "alloc") else val, self.fb[20], BG, r.center)

    @staticmethod
    def _value(v, key):
        if key[0] in ("alloc", "max", "need"):
            return getattr(v, key[0])[key[1]][key[2]]
        return {"avail": v.available, "work": v.work, "req": v.request}[key[0]][key[1]]

    def draw_banner(self, L, banner, a, t):
        if a <= 0.01:
            return
        txt, kind = banner
        col = BANNER[kind]
        tbl = L["table"]
        scale = 0.4 + 0.6 * a + (0.12 * math.sin(clamp(t / 0.25) * math.pi) if t < 0.25 else 0)
        img = self.fb[84].render(txt, True, (255, 255, 255))
        img = pygame.transform.smoothscale_by(img, scale) if hasattr(pygame.transform, "smoothscale_by") \
            else pygame.transform.smoothscale(img, (int(img.get_width() * scale), int(img.get_height() * scale)))
        # below the table when there is room, so the numbers stay readable
        cy = (tbl.bottom + 565) // 2 if tbl.bottom <= 430 else tbl.centery
        r = img.get_rect(center=(tbl.centerx, cy))
        self.rect(col, r.inflate(70, 30), 20, alpha=230 * a)
        img.set_alpha(int(255 * a))
        self.s.blit(img, r)

    def draw_title(self, title, a):
        big, small = title
        for y in range(0, 580, 4):
            c = mix((30, 27, 75), BG, y / 580)
            pygame.draw.rect(self.s, c, (0, y, W, 4))
        self.text(big, self.fb[60], TEXT, (W // 2, 250 - int((1 - a) * 30)), alpha=255 * a)
        if small:
            self.text(small, self.f[28], (165, 180, 252), (W // 2, 330), alpha=255 * a)
        pygame.draw.line(self.s, GROUP["work"], (W // 2 - 140 * a, 290), (W // 2 + 140 * a, 290), 3)

    def draw_caption(self, caption, info):
        box = pygame.Rect(30, 596, W - 60, 92)
        self.rect((2, 6, 23), box, 12, alpha=235)
        shown = caption[: int(len(caption) * info["caption_k"])]
        lines = self.wrap(caption, self.f[24], box.w - 40)
        used = 0
        y = box.y + 14 + (3 - len(lines)) * 13 if len(lines) < 3 else box.y + 8
        for line in lines:
            part = shown[used: used + len(line)]
            used += len(line) + 1
            if part:
                self.text(part, self.f[24], TEXT, (box.x + 20, y), "topleft")
            y += 28

    def draw_progress(self, info):
        bar = pygame.Rect(30, 700, W - 60, 8)
        self.rect(LINE, bar, 4)
        self.rect(RED, pygame.Rect(bar.x, bar.y, int(bar.w * info["progress"]), bar.h), 4)
        for frac, _ in info["chapters"]:
            x = bar.x + int(bar.w * frac)
            pygame.draw.rect(self.s, BG, (x - 1, bar.y, 3, bar.h))
        state = "PAUSED" if info["paused"] else f"{info['speed']:g}x"
        if info.get("hud", True):
            self.text(f"{state}   Space pause   <- -> step   Up/Down speed   1-{info['nsamples']} sample   R restart",
                      self.f[16], MUTED, (W - 32, 572), "midright")
