from __future__ import annotations

class Base:
    def __init__(self) -> None:
        self._events: list[str] = []

    def log(self, msg: str) -> None:
        self._events.append(msg)

    def events(self) -> list[str]:
        return list(self._events)


class ServiceBase(Base):
    def run(self) -> None:
        self.log("ServiceBase.run")

    def notify(self, repo: Repo, message: str) -> None:  # forward ref to Repo (defined in repo.py)
        # We intentionally only annotate by name; the crawler does not resolve types.
        self.log(f"notify:{message}")
        # Call into repository layer
        repo.save_event(self.__class__.__name__, message)
