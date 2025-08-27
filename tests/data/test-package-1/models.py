from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, Flag, auto
from typing import Any, NamedTuple


# Descriptor example
class UpperCase:
    def __set_name__(self, owner, name):
        self.private_name = f"_{name}"

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return getattr(obj, self.private_name, None)

    def __set__(self, obj, value):
        setattr(obj, self.private_name, None if value is None else str(value).upper())


class WithDescriptor:
    name = UpperCase()

    def __init__(self, name: str | None):
        self.name = name


# ABC and mixins
class Base(ABC):
    @abstractmethod
    def area(self) -> float:  # abstract method
        raise NotImplementedError

    @classmethod
    def from_unit(cls) -> "Base":
        return cls.default()

    @staticmethod
    def tau() -> float:
        return math.tau

    @property
    def is_shape(self) -> bool:
        return True

    @classmethod
    @abstractmethod
    def default(cls) -> "Base":
        raise NotImplementedError


class PrintableMixin:
    def __str__(self) -> str:
        return f"<{self.__class__.__name__}>"


class Concrete(PrintableMixin, Base):
    __slots__ = ("r",)

    def __init__(self, r: float = 1.0):
        self.r = r

    def area(self) -> float:
        return math.pi * self.r * self.r

    @classmethod
    def default(cls) -> "Concrete":
        return cls(1.0)


# Dunder methods and context manager
class Resource:
    def __init__(self, items: list[int]):
        self._items = items

    def __enter__(self) -> "Resource":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        # swallow nothing, just for API
        return False

    def __iter__(self):
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)


# Enums
class FancyEnum(Enum):
    SMALL = 1
    LARGE = 2


class Permission(Flag):
    READ = auto()
    WRITE = auto()
    EXEC = auto()


# NamedTuple and dataclass
class Point(NamedTuple):
    x: float
    y: float


@dataclass(frozen=True)
class FrozenCfg:
    path: str
    retries: int = 3
