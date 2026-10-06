"""Turns a scenario into a "video script": a list of Beats.

Each Beat has a narration caption, a chapter name, the View to show at the END
of the beat, and optional effects (flying numbers, staggered comparisons, ...).
The renderer animates from the previous beat's View to this one, so numbers
count up/down and colours fade automatically.
"""
import copy
from dataclasses import dataclass, field

import banker


def rname(j):
    return chr(65 + j) if j < 26 else f"R{j}"


def vec(v):
    return "(" + ", ".join(str(x) for x in v) + ")"


@dataclass
class View:
    n: int
    m: int
    alloc: list
    max: list
    need: list
    available: list
    rows_shown: float = 0          # how many table rows are visible (animates)
    need_shown: list = None        # per row: 0 hidden / 1 visible
    work: list = None              # None = Work box hidden
    request: list = None           # None = Request box hidden
    req_pid: int = None
    finish: list = None
    sequence: list = field(default_factory=list)
    row_hl: dict = field(default_factory=dict)   # row -> active|done|stuck|trial
    cell_hl: dict = field(default_factory=dict)  # cell key -> ok|bad|focus
    col_hl: set = field(default_factory=set)     # "alloc"/"max"/"need"/"avail"/"work"
    banner: tuple = None           # (text, kind) kind = ok|bad|wait|info
    title: tuple = None            # (big, small) -> full screen title card
    compare: tuple = None          # (left label, left vec, right label, right vec) shown under the boxes

    def copy(self, **kw):
        v = copy.deepcopy(self)
        for k, val in kw.items():
            setattr(v, k, val)
        return v


@dataclass
class Beat:
    chapter: str
    caption: str
    view: View
    effects: list = field(default_factory=list)
    duration: float = None   # seconds at 1x; None = from caption length

    def __post_init__(self):
        if self.duration is None:
            words = len(self.caption.split())
            self.duration = max(2.8, 0.9 + words * 0.32)


class _Builder:
    def __init__(self):
        self.beats = []
        self.v = None

    def beat(self, chapter, caption, effects=None, duration=None, **changes):
        self.v = self.v.copy(**changes)
        self.beats.append(Beat(chapter, caption, self.v, effects or [], duration))


def _safety_beats(b, state, chapter, label="Available"):
    """Append the beats that animate one run of the safety algorithm."""
    n, m = len(state["max"]), len(state["available"])
    res = banker.safety(state)
    need = banker.compute_need(state)
    last_pid = -1
    for st in res["steps"]:
        k = st["kind"]
        if k == "init":
            b.beat(chapter,
                   f"Start: copy Work = {label} = {vec(st['work'])}, and mark every process as not finished.",
                   effects=[("fly", [("avail", j) for j in range(m)], [("work", j) for j in range(m)])],
                   work=list(st["work"]), finish=[False] * n, sequence=[], row_hl={}, cell_hl={},
                   col_hl={"avail", "work"}, banner=None, compare=None)
            b.beat(chapter,
                   "Now we look for a process whose remaining Need fits inside Work. "
                   "If it fits, that process can run to completion.",
                   col_hl=set())
        elif k == "check":
            i = st["pid"]
            if i <= last_pid:
                b.beat(chapter, "End of the list. Some processes are still waiting, "
                                "so we go around again from the top with the bigger Work.",
                       row_hl={r: h for r, h in b.v.row_hl.items() if h == "done"}, cell_hl={}, compare=None,
                       duration=3.2)
            last_pid = i
            cells = {}
            for j in range(m):
                good = need[i][j] <= st["work"][j]
                cells[("need", i, j)] = "ok" if good else "bad"
                cells[("work", j)] = "ok" if good else "bad"
            hl = {r: h for r, h in b.v.row_hl.items() if h == "done"}
            hl[i] = "active"
            cmp = ("Need[P%d]" % i, need[i], "Work", st["work"])
            fails = [rname(j) for j in range(m) if need[i][j] > st["work"][j]]
            if st["ok"]:
                cap = (f"Check P{i}: Need {vec(need[i])} <= Work {vec(st['work'])}"
                       f"{' for every resource' if m > 1 else ''}. "
                       f"P{i} can finish!")
            else:
                cap = (f"Check P{i}: Need {vec(need[i])} vs Work {vec(st['work'])}. "
                       f"Not enough {', '.join(fails)}, so P{i} must wait. Skip it for now.")
            pairs = [(("need", i, j), ("work", j)) for j in range(m)]
            windows = {}
            for j, (a, c) in enumerate(pairs):
                w = (0.1 + 0.55 * j / m, 0.1 + 0.55 * (j + 1) / m)
                windows[a] = w
                windows[c] = w
            b.beat(chapter, cap, effects=[("stagger", windows)], row_hl=hl, cell_hl=cells, compare=cmp)
        elif k == "finish":
            i = st["pid"]
            hl = dict(b.v.row_hl)
            hl[i] = "done"
            b.beat(chapter,
                   f"P{i} runs, finishes, and gives back everything it holds: "
                   f"Work = {vec(st['before'])} + {vec(state['alloc'][i])} = {vec(st['work'])}. "
                   f"Add P{i} to the safe sequence.",
                   effects=[("fly", [("alloc", i, j) for j in range(m)], [("work", j) for j in range(m)])],
                   work=list(st["work"]), finish=list(st["finish"]), sequence=list(st["sequence"]),
                   row_hl=hl, cell_hl={}, compare=None, duration=None)
        elif k == "done":
            seq = ", ".join(f"P{p}" for p in st["sequence"])
            if st["safe"]:
                b.beat(chapter,
                       f"Every process can finish, so the state is SAFE. Safe sequence: <{seq}>.",
                       effects=[("pop",)], banner=("SAFE", "ok"), cell_hl={}, compare=None, duration=4.5)
            else:
                stuck = ", ".join(f"P{p}" for p in st["stuck"])
                hl = dict(b.v.row_hl)
                for p in st["stuck"]:
                    hl[p] = "stuck"
                b.beat(chapter,
                       f"Nobody in {{{stuck}}} has Need <= Work {vec(st['work'])}. "
                       "We can't guarantee they all finish: the state is UNSAFE (deadlock is possible).",
                       effects=[("pop",)], banner=("UNSAFE", "bad"), row_hl=hl, cell_hl={}, compare=None,
                       duration=5.5)
    return res


def build_script(sample):
    """Build the list of beats for one sample (or a custom state + optional request)."""
    state = sample["state"]
    n, m = len(state["max"]), len(state["available"])
    need = banker.compute_need(state)
    b = _Builder()
    b.v = View(n=n, m=m, alloc=copy.deepcopy(state["alloc"]), max=copy.deepcopy(state["max"]),
               need=copy.deepcopy(need), available=list(state["available"]), need_shown=[0] * n)
    res_names = ", ".join(rname(j) for j in range(m))

    # ---------------- Intro ----------------
    ch = "Introduction"
    b.beat(ch, "The Banker's Algorithm avoids deadlock: before giving resources to a process, "
               "the OS checks that everyone can still finish.",
           title=("Banker's Algorithm", sample.get("name", "Deadlock avoidance, step by step")), duration=5)
    b.beat(ch, sample.get("description") or f"{n} processes share {m} resource type(s).",
           title=("Banker's Algorithm", sample.get("name", "")), duration=5)
    b.beat(ch, f"Here are {n} processes, P0 to P{n - 1}, and {m} resource type{'s' if m > 1 else ''}: {res_names}.",
           title=None, rows_shown=n, effects=[("rows",)], duration=4)
    b.beat(ch, "Allocation: how many instances of each resource a process is holding right now.",
           col_hl={"alloc"})
    b.beat(ch, "Max: the most each process may ever ask for. Processes declare this in advance.",
           col_hl={"max"})
    b.beat(ch, f"Available: the free instances the OS still has. Right now that is {vec(state['available'])}.",
           col_hl={"avail"})

    # ---------------- Need ----------------
    ch = "Step 1: Compute Need"
    b.beat(ch, "First we compute Need = Max - Allocation: what each process may still request.",
           col_hl={"need"})
    shown = [0] * n
    detailed = min(n, 2)
    for i in range(detailed):
        shown = shown.copy()
        shown[i] = 1
        cells = {("max", i, j): "focus" for j in range(m)}
        cells.update({("alloc", i, j): "focus" for j in range(m)})
        b.beat(ch, f"P{i}: Max {vec(state['max'][i])} - Allocation {vec(state['alloc'][i])} = Need {vec(need[i])}.",
               need_shown=shown, cell_hl=cells, row_hl={i: "active"}, col_hl=set())
    if n > detailed:
        b.beat(ch, "The other processes are computed exactly the same way.",
               need_shown=[1] * n, cell_hl={}, row_hl={}, effects=[("stagger_rows", detailed)])
    b.beat(ch, "Now we have everything we need. Let's check if the system is in a safe state.",
           cell_hl={}, row_hl={}, col_hl={"need"}, duration=3.5)

    # ---------------- Safety ----------------
    res = _safety_beats(b, state, "Step 2: Safety Algorithm")

    # ---------------- Request ----------------
    rq = sample.get("request")
    if rq:
        ch = "Step 3: Resource Request"
        pid, req = rq["pid"], rq["req"]
        r = banker.request(state, pid, req)
        # reset the view to the real state
        b.beat(ch, f"Now a new event: P{pid} asks for {vec(req)}. Should the OS say yes?",
               request=list(req), req_pid=pid, work=None, finish=None, sequence=[], banner=None,
               row_hl={pid: "active"}, cell_hl={}, col_hl=set(), compare=None, duration=4)
        # check 1: request <= need
        ok1 = banker.leq(req, need[pid])
        cells = {}
        windows = {}
        for j in range(m):
            g = req[j] <= need[pid][j]
            cells[("req", j)] = cells[("need", pid, j)] = "ok" if g else "bad"
            windows[("req", j)] = windows[("need", pid, j)] = (0.1 + 0.55 * j / m, 0.1 + 0.55 * (j + 1) / m)
        b.beat(ch, f"Check 1: Request {vec(req)} <= Need {vec(need[pid])}? "
                   + ("Yes, P{} stays within what it declared.".format(pid) if ok1
                      else "No! P{} asks for more than it declared. That is an error.".format(pid)),
               cell_hl=cells, effects=[("stagger", windows)],
               compare=("Request", req, f"Need[P{pid}]", need[pid]))
        if not ok1:
            b.beat(ch, f"The request is DENIED immediately. P{pid} broke its promise about Max.",
                   effects=[("pop",)], banner=("DENIED", "bad"), cell_hl={}, compare=None, duration=4.5)
        else:
            ok2 = banker.leq(req, state["available"])
            cells, windows = {}, {}
            for j in range(m):
                g = req[j] <= state["available"][j]
                cells[("req", j)] = cells[("avail", j)] = "ok" if g else "bad"
                windows[("req", j)] = windows[("avail", j)] = (0.1 + 0.55 * j / m, 0.1 + 0.55 * (j + 1) / m)
            b.beat(ch, f"Check 2: Request {vec(req)} <= Available {vec(state['available'])}? "
                       + ("Yes, the resources exist right now." if ok2
                          else f"No. The OS doesn't have enough free right now, so P{pid} must WAIT."),
                   cell_hl=cells, effects=[("stagger", windows)],
                   compare=("Request", req, "Available", state["available"]))
            if not ok2:
                b.beat(ch, f"P{pid} WAITS until other processes release resources, then asks again.",
                       effects=[("pop",)], banner=("WAIT", "wait"), cell_hl={}, compare=None, duration=4.5)
            else:
                trial = r["trial"]
                t_need = banker.compute_need(trial)
                b.beat(ch, "Check 3: pretend we grant it. Available goes down, "
                           f"P{pid}'s Allocation goes up and its Need goes down by {vec(req)}.",
                       effects=[("fly", [("req", j) for j in range(m)], [("alloc", pid, j) for j in range(m)])],
                       available=list(trial["available"]), alloc=copy.deepcopy(trial["alloc"]),
                       need=t_need, cell_hl={("alloc", pid, j): "focus" for j in range(m)},
                       row_hl={pid: "trial"}, compare=None, duration=5)
                b.beat(ch, "This is only a trial state. Is it still safe? Run the Safety Algorithm again.",
                       cell_hl={}, duration=3.5)
                _safety_beats(b, trial, "Step 3: Safety check on trial state")
                if r["status"] == "granted":
                    b.beat("Result", f"The trial state is safe, so the request is GRANTED. "
                                     f"P{pid} gets {vec(req)} for real.",
                           effects=[("pop",)], banner=("GRANTED", "ok"), duration=4.5)
                else:
                    b.beat("Result", "The trial state is unsafe, so the request is DENIED. "
                                     f"Roll back: undo the pretend allocation, and P{pid} has to wait.",
                           effects=[("pop",)], banner=("DENIED", "bad"), duration=5)
                    b.beat("Result", "Rollback: Available, Allocation and Need return to their old values. "
                                     "Nothing was really given away.",
                           available=list(state["available"]), alloc=copy.deepcopy(state["alloc"]),
                           need=copy.deepcopy(need), work=None, finish=None, sequence=[], row_hl={},
                           banner=None, request=None, duration=5)

    # ---------------- Summary ----------------
    seq = ", ".join(f"P{p}" for p in res["sequence"])
    summary = (f"Summary: the starting state was {'SAFE, sequence <' + seq + '>' if res['safe'] else 'UNSAFE'}."
               + (f" Request from P{rq['pid']}: {banker.request(state, rq['pid'], rq['req'])['status'].upper()}."
                  if rq else ""))
    b.beat("Summary", summary, banner=None, row_hl={}, cell_hl={}, compare=None, duration=5)
    b.beat("Summary", "Remember: Banker grants a request only if the system can still find "
                      "an order in which every process finishes.",
           title=("That's the Banker's Algorithm!", "Need = Max - Allocation  |  Need <= Work  |  Work += Allocation"),
           duration=5)
    return b.beats
