from __future__ import annotations

from .base import ServiceBase
from .repo import Repo, AuditRepo
from .util import Helper

class UserService(ServiceBase):
    def __init__(self, repo: Repo | None = None) -> None:
        super().__init__()
        self.repo: Repo = repo or AuditRepo()
        self.helper = Helper()

    def run(self) -> None:
        super().run()
        self.helper.prepare(self)
        self.repo.save_event("UserService", "run")

    def create_user(self, name: str) -> None:
        # cross-class invocation inside same module via helper
        self.helper.validate_name(name)
        self.repo.save_event("UserService", f"create:{name}")

class AdminService(UserService):
    def run(self) -> None:
        # override and call base implementation
        super().run()
        self.repo.save_event("AdminService", "run")
