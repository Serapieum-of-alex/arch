from __future__ import annotations

import asyncio
import time
from typing import Any, Protocol, runtime_checkable, TypeVar, Generic, Literal

T = TypeVar("T")


# Metaclass that registers subclasses by name
class RegistryMeta(type):
    registry: dict[str, type] = {}

    def __new__(mcls, name, bases, ns, **kwargs):
        cls = super().__new__(mcls, name, bases, ns)
        # Only register non-abstract top-level classes
        if not name.startswith("Base") and name != "Pluggable":
            RegistryMeta.registry[name] = cls
        return cls


# Class decorator that marks classes

def tagged(tag: str):
    def deco(cls):
        cls.__tag__ = tag
        return cls

    return deco


# Simple descriptor for demonstration
class NonNegative:
    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, 0)

    def __set__(self, obj, value):
        if value < 0:
            raise ValueError("negative")
        setattr(obj, self.private_name, value)


# Protocols
@runtime_checkable
class BasePlugin(Protocol):
    name: str

    def run(self, data: str) -> str:
        ...


# Generic container
class Box(Generic[T]):
    def __init__(self, value: T):
        self.value = value

    def map(self, fn: callable[[T], T]) -> "Box[T]":
        return Box(fn(self.value))


class Pluggable(metaclass=RegistryMeta):
    counter = NonNegative()

    def __init__(self):
        self.counter = 0

    def register(self, plugin: BasePlugin) -> None:
        # demonstrate Literal and union return typing
        self.last: str | None = plugin.run("init")


@tagged("concrete")
class ConcretePlugin(Pluggable):
    name = "concrete"

    def run(self, data: str) -> str:  # type: ignore[override]
        return f"{self.name}:{data}"


# Async context manager
class AsyncTimer:
    async def __aenter__(self):
        self._start = time.perf_counter()
        await asyncio.sleep(0)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await asyncio.sleep(0)
        self.elapsed = time.perf_counter() - self._start


# Example async function using the timer
async def timed_double(x: int) -> int:
    async with AsyncTimer() as t:  # noqa: F841
        await asyncio.sleep(0)
        return x * 2
