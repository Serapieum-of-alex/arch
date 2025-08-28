from typing import Callable, Any

def deco1(fn: Callable[..., Any]) -> Callable[..., Any]:
    def w(*a, **k):
        return fn(*a, **k)
    return w


def deco2(fn: Callable[..., Any]) -> Callable[..., Any]:
    def w(*a, **k):
        return fn(*a, **k)
    return w


@deco1
@deco2
def multi(x: int) -> int:
    return x