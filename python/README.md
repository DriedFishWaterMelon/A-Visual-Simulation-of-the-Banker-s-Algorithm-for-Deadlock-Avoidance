# Banker's Algorithm — animated explainer (Python)

An "explainer video" style animation of the Banker's Algorithm: smooth transitions,
numbers that fly and count up, colour-coded comparisons, and a narration caption for every step.
It plays in a window (pause / step / speed / seek), or exports an MP4 you can upload or put in slides.

## Install & run

```
pip install -r requirements.txt     # just pygame
python main.py                      # sample 1 in a window
python main.py --sample 2           # samples 1-6 (same as the web version)
python main.py --json state.json    # your own data (the web version's "save" file works)
```

Export a video (needs [ffmpeg](https://ffmpeg.org) on PATH):

```
python main.py --sample 1 --record banker.mp4
python main.py --all --record banker_all.mp4      # all 6 samples in one video
python main.py --sample 2 --speed 1.5 --record fast.mp4
```

## Google Colab

Open [`banker_colab.ipynb`](banker_colab.ipynb) in Colab (`File → Upload notebook`, or
[open it straight from GitHub](https://colab.research.google.com/github/DriedFishWaterMelon/A-Visual-Simulation-of-the-Banker-s-Algorithm-for-Deadlock-Avoidance/blob/main/python/banker_colab.ipynb)
if the repo is public), then `Runtime → Run all`. It renders the video and plays it in the notebook,
and also has a step-by-step slider viewer. Pick a sample or type your own data in the form.
The notebook is self-contained; after changing the `.py` files, rebuild it with `python make_notebook.py`.

## Controls

| Key | Action |
|---|---|
| Space | pause / play |
| → / ← | next / previous step |
| ↑ / ↓ | faster / slower (0.25x – 3x) |
| 1 – 6 | switch sample |
| R | restart |
| H | hide key hints |
| click progress bar | jump |
| Esc | quit |

## What the video shows

1. **Introduction** – the processes, Allocation, Max, Available
2. **Step 1: Need = Max − Allocation** – worked out row by row
3. **Step 2: Safety algorithm** – Work = Available, then each `Need ≤ Work` check is revealed
   resource by resource (green ≤ / red >), finished processes hand their Allocation back to
   Work (flying numbers), the safe sequence builds up, ending with a SAFE / UNSAFE banner
4. **Step 3: Resource request** – Request ≤ Need?, Request ≤ Available?, pretend to allocate,
   run the safety check on the trial state, then GRANTED / WAIT / DENIED (with rollback)
5. **Summary**

## JSON input

```json
{
  "available": [3, 3, 2],
  "max":   [[7,5,3], [3,2,2], [9,0,2], [2,2,2], [4,3,3]],
  "alloc": [[0,1,0], [2,0,0], [3,0,2], [2,1,1], [0,0,2]],
  "request": { "pid": 1, "req": [1, 0, 2] }
}
```
`request` is optional.

## Files

```
banker.py       algorithm only (safety + request), records every step
samples.py      the 6 sample scenarios with hand-checked answers
script.py       turns a scenario into "beats": narration + what the screen shows
render.py       draws a frame, animating from the previous beat to the current one
main.py         window / controls / MP4 export
make_notebook.py  builds banker_colab.ipynb from the files above
test_banker.py  python test_banker.py
```
