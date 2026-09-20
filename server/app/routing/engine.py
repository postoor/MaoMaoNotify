"""Routing engine (§23, §24, §53).

Pure planner: given the routing mode, priority, the presence-ordered active
devices, and the user's full device list, produce an ordered list of target
devices plus the fallback timeout. Delivery/ACK orchestration lives in
``app.notifications.delivery``.
"""

from dataclasses import dataclass, field

from app.notifications import constants as c


@dataclass
class RoutingPlan:
    mode: str
    targets: list[str] = field(default_factory=list)  # ordered; primary first
    timeout_seconds: int = 5


def _dedup(seq: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def plan_routes(
    mode: str,
    priority: str,
    ordered_active: list[str],
    all_devices: list[str],
    specific_device: str | None = None,
) -> RoutingPlan:
    timeout = c.FALLBACK_TIMEOUT.get(priority, c.FALLBACK_TIMEOUT[c.PRIORITY_NORMAL])

    if mode == c.ROUTE_SPECIFIC_DEVICE:
        targets = [specific_device] if specific_device else []
    elif mode == c.ROUTE_ALL_DEVICES:
        # active devices first (better ordering), then the rest
        targets = _dedup([*ordered_active, *all_devices])
    elif mode == c.ROUTE_ACTIVE_ONLY:
        targets = ordered_active[:1]
    else:  # active_with_fallback (default)
        if priority == c.PRIORITY_LOW:
            targets = ordered_active[:1]  # low → primary only (§23)
        else:
            targets = list(ordered_active)
        if not targets:
            # no known active device → best-effort fan-out so nothing is lost
            targets = _dedup(all_devices)

    return RoutingPlan(mode=mode, targets=targets, timeout_seconds=timeout)
