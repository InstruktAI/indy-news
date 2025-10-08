from collections.abc import Generator
from contextlib import contextmanager
from threading import Lock
from typing import Any

namespace_lock = Lock()
namespace: dict[str, Lock] = {}
counters: dict[str, int] = {}


@contextmanager
def parameterized_lock(
    value: Any,
    blocking: bool = True,
    timeout: float = -1.0,
) -> Generator[bool, None, None]:
    try:
        with namespace_lock:
            if value in namespace:
                counters[value] += 1
            else:
                namespace[value] = Lock()
                counters[value] = 1

        yield namespace[value].acquire(blocking=blocking, timeout=timeout)
    finally:
        with namespace_lock:
            if counters[value] == 1:
                del counters[value]
                lock = namespace.pop(value)
            else:
                counters[value] -= 1
                lock = namespace[value]
        lock.release()
