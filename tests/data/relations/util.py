from __future__ import annotations

from .repo import Repo

class Helper:
    def prepare(self, service: object) -> None:
        # pretend heavy prep
        if hasattr(service, "log"):
            service.log("Helper.prepare")

    def validate_name(self, name: str) -> None:
        if not name or not name.strip():
            raise ValueError("empty name")


def util_function(x: int) -> int:
    return x * 2
