from __future__ import annotations

from ..service import UserService

class PluginBase:
    def activate(self, svc: UserService) -> None:
        svc.create_user("plugin-user")

class ConcretePlugin(PluginBase):
    def activate(self, svc: UserService) -> None:
        super().activate(svc)
        svc.repo.save_event("ConcretePlugin", "activate")
