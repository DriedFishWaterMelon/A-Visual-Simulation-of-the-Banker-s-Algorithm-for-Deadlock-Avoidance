"""Banker's Algorithm — animated explainer (pygame).

    python main.py                     play sample 1 in a window
    python main.py --sample 2          pick a sample (1-6)
    python main.py --json state.json   your own data (same JSON as the web version's "save")
    python main.py --record out.mp4    render a video file instead of opening a window (needs ffmpeg)

Keys: Space pause/play, Left/Right previous/next step, Up/Down speed,
      1-6 switch sample, R restart, H hide/show key hints, Esc quit.
      Click the progress bar to jump.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

import banker
from samples import SAMPLES
from script import build_script

FPS = 60


class Player:
    def __init__(self, sample):
        self.load(sample)
        self.speed = 1.0
        self.paused = False
        self.hud = True

    def load(self, sample):
        self.sample = sample
        self.beats = build_script(sample)
        self.starts = []
        acc = 0.0
        for b in self.beats:
            self.starts.append(acc)
            acc += b.duration
        self.total = acc
        self.idx = 0
        self.t = 0.0  # seconds into current beat
        self.chapters = []
        last = None
        for b, s in zip(self.beats, self.starts):
            if b.chapter != last:
                self.chapters.append((s / self.total, b.chapter))
                last = b.chapter

    @property
    def finished(self):
        return self.idx == len(self.beats) - 1 and self.t >= self.beats[-1].duration

    def update(self, dt):
        if self.paused or self.finished:
            return
        self.t += dt * self.speed
        while self.t >= self.beats[self.idx].duration and self.idx < len(self.beats) - 1:
            self.t -= self.beats[self.idx].duration
            self.idx += 1
        self.t = min(self.t, self.beats[self.idx].duration)

    def jump(self, idx, at_end=False):
        self.idx = max(0, min(len(self.beats) - 1, idx))
        self.t = self.beats[self.idx].duration if at_end else 0.0

    def seek(self, frac):
        target = frac * self.total
        for i, s in enumerate(self.starts):
            if s <= target < s + self.beats[i].duration:
                self.idx, self.t = i, target - s
                return

    def frame_info(self):
        b = self.beats[self.idx]
        k = min(1.0, self.t / min(1.6, b.duration * 0.45))
        return {
            "chapter": b.chapter,
            "progress": (self.starts[self.idx] + self.t) / self.total,
            "chapters": self.chapters,
            "caption_k": k,
            "paused": self.paused,
            "speed": self.speed,
            "sample": self.sample.get("name", ""),
            "nsamples": len(SAMPLES),
            "hud": self.hud,
        }

    def draw(self, renderer):
        b = self.beats[self.idx]
        prev = self.beats[self.idx - 1].view if self.idx > 0 else None
        renderer.draw(b, prev, self.t / b.duration, self.frame_info())


def load_json(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    state = {"available": data["available"], "max": data["max"], "alloc": data["alloc"]}
    errors = banker.validate_state(state)
    if errors:
        sys.exit("Invalid input:\n  " + "\n  ".join(errors))
    sample = {"name": os.path.basename(path), "description": "", "state": state}
    if "request" in data:
        sample["request"] = {"pid": data["request"]["pid"], "req": data["request"]["req"]}
    return sample


def run_window(player):
    import pygame
    from render import W, H, Renderer

    pygame.init()
    screen = pygame.display.set_mode((W, H), pygame.SCALED | pygame.RESIZABLE)
    pygame.display.set_caption("Banker's Algorithm — animated")
    renderer = Renderer(screen)
    clock = pygame.time.Clock()
    speeds = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 3.0]
    while True:
        dt = clock.tick(FPS) / 1000
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                return
            if e.type == pygame.KEYDOWN:
                if e.key in (pygame.K_ESCAPE, pygame.K_q):
                    return
                elif e.key == pygame.K_SPACE:
                    if player.finished:
                        player.jump(0)
                        player.paused = False
                    else:
                        player.paused = not player.paused
                elif e.key == pygame.K_RIGHT:
                    # finish the current beat first, then move on
                    if player.t < player.beats[player.idx].duration - 1e-3:
                        player.jump(player.idx, at_end=True)
                    else:
                        player.jump(player.idx + 1, at_end=player.paused)
                elif e.key == pygame.K_LEFT:
                    player.jump(player.idx - (1 if player.t < 0.6 else 0), at_end=player.paused)
                elif e.key == pygame.K_UP:
                    player.speed = next((s for s in speeds if s > player.speed), speeds[-1])
                elif e.key == pygame.K_DOWN:
                    player.speed = next((s for s in reversed(speeds) if s < player.speed), speeds[0])
                elif e.key == pygame.K_r:
                    player.jump(0)
                    player.paused = False
                elif e.key == pygame.K_h:
                    player.hud = not player.hud
                elif pygame.K_1 <= e.key <= pygame.K_9 and e.key - pygame.K_1 < len(SAMPLES):
                    player.load(SAMPLES[e.key - pygame.K_1])
                    player.paused = False
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1 and 690 <= e.pos[1] <= 718:
                player.seek(max(0.0, min(0.999, (e.pos[0] - 30) / (W - 60))))
        player.update(dt)
        player.draw(renderer)
        pygame.display.flip()


def record(players, out, fps=30):
    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found. Install it (https://ffmpeg.org) to export video.")
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame
    from render import W, H, Renderer

    pygame.init()
    pygame.display.set_mode((1, 1))
    surface = pygame.Surface((W, H))
    renderer = Renderer(surface)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", out]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    tobytes = getattr(pygame.image, "tobytes", None) or pygame.image.tostring
    frames = 0
    for player in players:
        player.hud = False
        while True:
            player.draw(renderer)
            proc.stdin.write(tobytes(surface, "RGB"))
            frames += 1
            if player.finished:
                break
            player.update(1 / fps)
        for _ in range(fps):  # hold the last frame for a second
            proc.stdin.write(tobytes(surface, "RGB"))
            frames += 1
        print(f"  rendered {player.sample['name']}")
    proc.stdin.close()
    proc.wait()
    print(f"Saved {out} ({frames / fps:.0f} s)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=1, help=f"sample number 1-{len(SAMPLES)}")
    ap.add_argument("--json", help="load state (+ optional request) from a JSON file")
    ap.add_argument("--record", metavar="OUT.mp4", help="render to a video file instead of a window")
    ap.add_argument("--all", action="store_true", help="with --record: put every sample in one video")
    ap.add_argument("--speed", type=float, default=1.0, help="playback speed (default 1.0)")
    args = ap.parse_args()

    if args.json:
        samples = [load_json(args.json)]
    elif args.all:
        samples = SAMPLES
    else:
        if not 1 <= args.sample <= len(SAMPLES):
            ap.error(f"--sample must be 1-{len(SAMPLES)}")
        samples = [SAMPLES[args.sample - 1]]

    players = [Player(s) for s in samples]
    for p in players:
        p.speed = args.speed
    if args.record:
        record(players, args.record)
    else:
        run_window(players[0])


if __name__ == "__main__":
    main()
