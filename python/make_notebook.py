"""Builds banker_colab.ipynb from the .py files in this folder, so the notebook never drifts.

    python make_notebook.py
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
MODULES = ["banker.py", "samples.py", "script.py", "render.py", "main.py"]


def md(text):
    return {"cell_type": "markdown", "metadata": {}, "source": text.strip("\n").splitlines(True)}


def code(text):
    return {"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [],
            "source": text.strip("\n").splitlines(True)}


cells = [
    md("""
# Banker's Algorithm — animated explainer (Colab)

An explainer-video style animation of the Banker's Algorithm (deadlock avoidance):
numbers fly and count up, every `Need ≤ Work` check is coloured resource by resource,
and every step has a narration caption.

**How to use:** `Runtime → Run all`, or run the cells from top to bottom.

1. **Setup** installs pygame and writes the program files
2. **Choose the data**: one of the 6 samples, or type your own
3. **Watch the video**: renders an MP4 and plays it here (you can download it)
4. **Step through**: go step by step with a slider, without rendering a video
"""),
    md("## 1. Setup"),
    code("""
#@title Install pygame (run once)
!pip -q install pygame
import os
os.environ["SDL_VIDEODRIVER"] = "dummy"   # no screen in Colab: draw off-screen
os.environ["SDL_AUDIODRIVER"] = "dummy"
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"
"""),
    md("""
The next cells write the program's source files (the same files as the `python/` folder in the repo).
You don't need to read them; just run them.
"""),
]

for name in MODULES:
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        src = f.read()
    cells.append(code(f"%%writefile {name}\n{src}"))

cells += [
    md("## 2. Choose the data"),
    code("""
#@title Pick a sample, or use your own data
#@markdown **Samples:** 1) safe + granted · 2) denied (unsafe) · 3) exceeds Need · 4) wait · 5) one resource, unsafe · 6) already unsafe
sample_number = 1  #@param {type:"slider", min:1, max:6, step:1}
use_my_own_data = False  #@param {type:"boolean"}
#@markdown ---
#@markdown **Your own data** (used only when the box above is ticked). Numbers separated by spaces, rows by `;`
available = "3 3 2"  #@param {type:"string"}
max_matrix = "7 5 3; 3 2 2; 9 0 2; 2 2 2; 4 3 3"  #@param {type:"string"}
allocation = "0 1 0; 2 0 0; 3 0 2; 2 1 1; 0 0 2"  #@param {type:"string"}
#@markdown Request (leave `request` empty to skip the request part)
request_process = 1  #@param {type:"integer"}
request = "1 0 2"  #@param {type:"string"}

import importlib, banker, samples
importlib.reload(banker); importlib.reload(samples)

def _vec(s):
    return [int(x) for x in s.replace(",", " ").split()]

def _mat(s):
    return [_vec(r) for r in s.split(";") if r.strip()]

if use_my_own_data:
    state = {"available": _vec(available), "max": _mat(max_matrix), "alloc": _mat(allocation)}
    errors = banker.validate_state(state)
    if errors:
        raise ValueError("Please fix the data:\\n  " + "\\n  ".join(errors))
    chosen = {"name": "My data", "description": "", "state": state}
    if request.strip():
        chosen["request"] = {"pid": request_process, "req": _vec(request)}
else:
    chosen = samples.SAMPLES[sample_number - 1]

need = banker.compute_need(chosen["state"])
res = banker.safety(chosen["state"])
print("Scenario :", chosen["name"])
print("Need     :", need)
print("Safe?    :", res["safe"], "  sequence:", ["P%d" % p for p in res["sequence"]])
if "request" in chosen:
    r = banker.request(chosen["state"], chosen["request"]["pid"], chosen["request"]["req"])
    print("Request  : P%d asks %s -> %s (%s)" % (chosen["request"]["pid"], chosen["request"]["req"],
                                               r["status"].upper(), r["code"]))
"""),
    md("## 3. Watch the video"),
    code("""
#@title Render the video and play it (takes about a minute)
speed = 1.0  #@param {type:"slider", min:0.5, max:3, step:0.25}
fps = 24  #@param [24, 30] {type:"raw"}
download_after = False  #@param {type:"boolean"}

import importlib, base64, main, script, render
for mod in (script, render, main):
    importlib.reload(mod)
from IPython.display import HTML, display

player = main.Player(chosen)
player.speed = speed
print(f"{len(player.beats)} steps, about {player.total / speed / 60:.1f} min of video. Rendering...")
main.record([player], "banker.mp4", fps=fps)

with open("banker.mp4", "rb") as f:
    data = base64.b64encode(f.read()).decode()
display(HTML(f'<video width="960" controls autoplay><source src="data:video/mp4;base64,{data}" type="video/mp4"></video>'))

if download_after:
    from google.colab import files
    files.download("banker.mp4")
"""),
    md("## 4. Step through (no video needed)"),
    code("""
#@title Step-by-step viewer: press ▶ or drag the slider
import importlib, io, main, script, render
for mod in (script, render, main):
    importlib.reload(mod)
import pygame
import ipywidgets as widgets
from IPython.display import display

pygame.init()
pygame.display.set_mode((1, 1))
_surface = pygame.Surface((render.W, render.H))
_renderer = render.Renderer(_surface)
_viewer = main.Player(chosen)
_viewer.hud = False

def _frame(i):
    _viewer.idx = i
    _viewer.t = _viewer.beats[i].duration   # end of the step: animation done, caption complete
    _viewer.draw(_renderer)
    buf = io.BytesIO()
    pygame.image.save(_surface, buf, "frame.png")
    return buf.getvalue()

_frames = [_frame(i) for i in range(len(_viewer.beats))]
n = len(_frames)
image = widgets.Image(value=_frames[0], format="png", width=960)
slider = widgets.IntSlider(min=0, max=n - 1, description="Step", layout=widgets.Layout(width="600px"))
play = widgets.Play(min=0, max=n - 1, interval=3500, description="Play")
widgets.jslink((play, "value"), (slider, "value"))
label = widgets.HTML()

def _show(change=None):
    i = slider.value
    image.value = _frames[i]
    b = _viewer.beats[i]
    label.value = f"<b>{i + 1}/{n} · {b.chapter}</b><br>{b.caption}"

slider.observe(_show, names="value")
_show()
display(widgets.VBox([widgets.HBox([play, slider]), label, image]))
"""),
    md("""
---
**Tip:** for a single video with all 6 samples, run:
```python
main.record([main.Player(s) for s in samples.SAMPLES], "banker_all.mp4", fps=24)
```
"""),
]

nb = {
    "nbformat": 4,
    "nbformat_minor": 0,
    "metadata": {
        "colab": {"provenance": [], "toc_visible": True},
        "kernelspec": {"name": "python3", "display_name": "Python 3"},
        "language_info": {"name": "python"},
    },
    "cells": cells,
}

out = os.path.join(HERE, "banker_colab.ipynb")
with open(out, "w", encoding="utf-8") as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("wrote", out)
