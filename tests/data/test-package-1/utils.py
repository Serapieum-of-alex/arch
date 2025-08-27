from __future__ import annotations

import functools
from dataclasses import dataclass, field, make_dataclass
from functools import lru_cache, partial
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    NamedTuple,
    NewType,
    TypedDict,
    TypeAlias,
    overload,
)
from functools import singledispatch

# Type aliases and NewType
JSONLike: TypeAlias = dict[str, Any] | list[Any] | str | int | float | bool | None
UserId = NewType("UserId", int)


# TypedDict
class Config(TypedDict, total=False):
    host: str
    port: int
    debug: bool


# NamedTuple
class Pair(NamedTuple):
    left: int
    right: int


# Dataclass
@dataclass
class Record:
    id: int
    name: str
    tags: list[str] = field(default_factory=list)


# Factory that returns a dataclass-like class at runtime

def make_dataclass_like(class_name: str = "DynRec") -> type:
    return make_dataclass(class_name, [
        ("key", int),
        ("value", str, field(default="")),
    ])


# singledispatch function
@singledispatch
def stringify(obj: Any) -> str:
    return str(obj)


@stringify.register
def _(obj: int) -> str:  # type: ignore[misc]
    return f"<int {obj}>"


@stringify.register
def _(obj: list) -> str:  # type: ignore[misc]
    return f"list({', '.join(map(str, obj))})"


# lru_cache example
@lru_cache(maxsize=64)
def cached_fib(n: int) -> int:
    if n < 2:
        return n
    return cached_fib(n - 1) + cached_fib(n - 2)


# Higher-order utilities

def map_apply(fn: Callable[[Any], Any], items: Iterable[Any]) -> list[Any]:
    return [fn(x) for x in items]


# Partial application example
incr_by = lambda k: partial(lambda a, b: a + b, k)  # noqa: E731


# Overloads for a simple parse function
@overload
def parse(value: int) -> int: ...


@overload
def parse(value: str) -> int: ...


def parse(value: int | str) -> int:
    if isinstance(value, int):
        return value
    return int(value)


# Iterator example using a generator function

def iter_records(records: Iterable[Record]) -> Iterator[str]:
    for r in records:
        yield f"{r.id}:{r.name}"


# A simple alias used elsewhere
StrDict: TypeAlias = dict[str, str]
