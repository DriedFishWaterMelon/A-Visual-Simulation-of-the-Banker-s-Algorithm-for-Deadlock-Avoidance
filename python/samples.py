"""Sample scenarios with hand-checked answers (same data as samples/samples.js)."""

_BASE = {
    "available": [3, 3, 2],
    "max": [[7, 5, 3], [3, 2, 2], [9, 0, 2], [2, 2, 2], [4, 3, 3]],
    "alloc": [[0, 1, 0], [2, 0, 0], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
}
# state after P1's request (1,0,2) was granted
_AFTER_P1 = {
    "available": [2, 3, 0],
    "max": _BASE["max"],
    "alloc": [[0, 1, 0], [3, 0, 2], [3, 0, 2], [2, 1, 1], [0, 0, 2]],
}


def _tape(alloc, available):
    return {"available": available, "max": [[10], [4], [9]], "alloc": alloc}


SAMPLES = [
    {
        "name": "1) Safe state + request granted",
        "description": "Textbook example: 5 processes, 3 resources (A=10, B=5, C=7). P1 requests (1,0,2).",
        "state": _BASE,
        "request": {"pid": 1, "req": [1, 0, 2]},
        "expected": {"safe": True, "sequence": [1, 3, 4, 0, 2], "status": "granted", "code": "GRANTED"},
    },
    {
        "name": "2) Request denied: would be unsafe",
        "description": "After P1 got (1,0,2), P0 requests (0,2,0). Resources exist, but granting is unsafe.",
        "state": _AFTER_P1,
        "request": {"pid": 0, "req": [0, 2, 0]},
        "expected": {"safe": True, "sequence": [1, 3, 4, 0, 2], "status": "denied", "code": "UNSAFE"},
    },
    {
        "name": "3) Request exceeds Need",
        "description": "P1 has Need (1,2,2) but requests (3,0,0): more than it declared.",
        "state": _BASE,
        "request": {"pid": 1, "req": [3, 0, 0]},
        "expected": {"safe": True, "sequence": [1, 3, 4, 0, 2], "status": "denied", "code": "EXCEEDS_NEED"},
    },
    {
        "name": "4) Not enough available: wait",
        "description": "P4 requests (3,3,0) within its Need (4,3,1), but only (2,3,0) is free.",
        "state": _AFTER_P1,
        "request": {"pid": 4, "req": [3, 3, 0]},
        "expected": {"safe": True, "sequence": [1, 3, 4, 0, 2], "status": "wait", "code": "NOT_AVAILABLE"},
    },
    {
        "name": "5) One resource type: +1 makes it unsafe",
        "description": "12 tape drives (Max 10, 4, 9). Safe now, but giving P2 one more is unsafe.",
        "state": _tape([[5], [2], [2]], [3]),
        "request": {"pid": 2, "req": [1]},
        "expected": {"safe": True, "sequence": [1, 0, 2], "status": "denied", "code": "UNSAFE"},
    },
    {
        "name": "6) Starting state is already unsafe",
        "description": "Sample 5 after P2 got the extra drive anyway (no Banker). Only P1 can finish.",
        "state": _tape([[5], [2], [3]], [2]),
        "request": {"pid": 1, "req": [2]},
        "expected": {"safe": False, "sequence": [1], "status": "denied", "code": "UNSAFE"},
    },
]
