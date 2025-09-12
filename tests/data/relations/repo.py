from __future__ import annotations

class Repo:
    def __init__(self) -> None:
        self._data: list[str] = []

    def save_event(self, source: str, message: str) -> None:
        self._data.append(f"{source}:{message}")

    def get_all(self) -> list[str]:
        return list(self._data)

class AuditRepo(Repo):
    def save_event(self, source: str, message: str) -> None:
        super().save_event(source, f"AUDIT:{message}")
