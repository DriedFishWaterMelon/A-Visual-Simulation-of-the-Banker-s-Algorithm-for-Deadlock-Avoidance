"""Banker's Algorithm core (no drawing code). Mirrors core/banker.js.

state = {"available": [m], "max": [[n][m]], "alloc": [[n][m]]}
Need is always computed as Max - Allocation, never stored.
safety() records every step so the animation can replay it.
"""
import copy


def leq(a, b):
    return all(x <= y for x, y in zip(a, b))


def add(a, b):
    return [x + y for x, y in zip(a, b)]


def sub(a, b):
    return [x - y for x, y in zip(a, b)]


def is_nonneg_int(v):
    return isinstance(v, int) and not isinstance(v, bool) and v >= 0


def compute_need(state):
    return [[mx - al for mx, al in zip(mrow, arow)] for mrow, arow in zip(state["max"], state["alloc"])]


def validate_state(s):
    """Return a list of error messages ([] means the state is usable)."""
    errors = []
    n, m = len(s.get("max", [])), len(s.get("available", []))
    if n == 0 or m == 0:
        return ["need at least 1 process and 1 resource"]
    if len(s.get("alloc", [])) != n:
        errors.append("Allocation and Max have a different number of rows")
        return errors
    for j, v in enumerate(s["available"]):
        if not is_nonneg_int(v):
            errors.append(f"Available[{j}] must be a non-negative integer")
    for i in range(n):
        if len(s["max"][i]) != m or len(s["alloc"][i]) != m:
            errors.append(f"P{i}: column count does not match the number of resources")
            continue
        for j in range(m):
            mx, al = s["max"][i][j], s["alloc"][i][j]
            if not is_nonneg_int(mx) or not is_nonneg_int(al):
                errors.append(f"P{i} column {j}: Max and Allocation must be non-negative integers")
            elif mx < al:
                errors.append(f"P{i} column {j}: Max ({mx}) < Allocation ({al}) makes Need negative")
    return errors


def safety(state):
    """Safety algorithm. Scans P0..Pn-1 repeatedly until nobody else can finish.

    Returns {"safe", "sequence", "steps"}; each step is a dict with
    kind in init|check|finish|done plus work/finish/sequence snapshots.
    """
    n = len(state["max"])
    need = compute_need(state)
    work = list(state["available"])
    finish = [False] * n
    sequence = []
    steps = []

    def snap(**kw):
        kw.update(work=list(work), finish=list(finish), sequence=list(sequence))
        steps.append(kw)

    snap(kind="init")
    progress = True
    while len(sequence) < n and progress:
        progress = False
        for i in range(n):
            if finish[i]:
                continue
            ok = leq(need[i], work)
            snap(kind="check", pid=i, ok=ok, need=list(need[i]))
            if ok:
                before = work
                work = add(work, state["alloc"][i])
                finish[i] = True
                sequence.append(i)
                progress = True
                snap(kind="finish", pid=i, before=list(before))
    safe = len(sequence) == n
    snap(kind="done", safe=safe, stuck=[i for i in range(n) if not finish[i]])
    return {"safe": safe, "sequence": sequence, "steps": steps}


def request(state, pid, req):
    """Resource-request algorithm.

    Returns {"status": granted|wait|denied|invalid, "code", "trial", "safety", "new_state"}.
    """
    m = len(state["available"])
    if not isinstance(pid, int) or not 0 <= pid < len(state["max"]):
        return {"status": "invalid", "code": "BAD_PID", "new_state": state}
    if len(req) != m or not all(is_nonneg_int(v) for v in req):
        return {"status": "invalid", "code": "BAD_REQUEST", "new_state": state}
    need = compute_need(state)[pid]
    if not leq(req, need):
        return {"status": "denied", "code": "EXCEEDS_NEED", "new_state": state}
    if not leq(req, state["available"]):
        return {"status": "wait", "code": "NOT_AVAILABLE", "new_state": state}
    trial = copy.deepcopy(state)
    trial["available"] = sub(trial["available"], req)
    trial["alloc"][pid] = add(trial["alloc"][pid], req)
    s = safety(trial)
    if s["safe"]:
        return {"status": "granted", "code": "GRANTED", "trial": trial, "safety": s, "new_state": trial}
    return {"status": "denied", "code": "UNSAFE", "trial": trial, "safety": s, "new_state": state}
