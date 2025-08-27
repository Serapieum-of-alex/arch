from __future__ import annotations

import math
from enum import Enum, auto
from contextlib import contextmanager
from pathlib import Path
from typing import Callable, Iterator, Any

# Module-level constants and annotations
PI: float = math.pi
COLORS: list[str] = ["red", "green", "blue"]


class Color(Enum):
    RED = auto()
    GREEN = auto()
    BLUE = auto()


# Decorators
def simple_deco(fn: Callable[..., Any]) -> Callable[..., Any]:
    def wrapper(*args, **kwargs):
        return fn(*args, **kwargs)

    wrapper.__name__ = fn.__name__
    return wrapper


def times(n: int) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def deco(fn: Callable[..., Any]) -> Callable[..., Any]:
        def wrapper(*args, **kwargs):
            result = None
            for _ in range(n):
                result = fn(*args, **kwargs)
            return result

        return wrapper

    return deco


@simple_deco
def greet(name: str = "World") -> str:
    return f"Hello, {name}!"


@times(2)
def add(a: int, b: int) -> int:
    return a + b


async def async_add(a: int, b: int) -> int:
    return a + b


# Closure / factory
def make_counter(start: int = 0) -> Callable[[], int]:
    count = start

    def inc() -> int:
        nonlocal count
        count += 1
        return count

    return inc


# Generator
def count_up_to(n: int) -> Iterator[int]:
    i = 0
    while i <= n:
        yield i
        i += 1


# Context manager
@contextmanager
def opened(path: str | Path, mode: str = "r", encoding: str | None = "utf-8") -> Iterator[Any]:
    f = open(path, mode, encoding=encoding)  # noqa: P201
    try:
        yield f
    finally:
        f.close()


# Comprehensions, walrus, pattern matching

def classify_numbers(nums: list[int]) -> dict[str, list[int]]:
    evens = [n for n in nums if (n % 2 == 0)]
    odds = [n for n in nums if n % 2]
    squares = {n: (n * n) for n in nums}
    # Walrus example outside of a comprehension condition to keep syntax simple
    first = (x := nums[0]) if nums else None  # noqa: F841
    match len(nums):
        case 0:
            size = "empty"
        case 1:
            size = "single"
        case _ if len(nums) < 5:
            size = "small"
        case _:
            size = "big"
    return {"evens": evens, "odds": odds, "size": [len(nums)], "sq_keys": list(squares.keys())}


# I/O helper

def read_file(path: str | Path) -> str:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(p)
    with opened(p, "r", encoding="utf-8") as fh:
        return fh.read()


# Lambda, partial usage covered in utils
noop = lambda x: x  # noqa: E731
