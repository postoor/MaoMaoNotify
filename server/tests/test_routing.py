"""Routing planner (§23, §24, §53)."""

from app.notifications import constants as c
from app.routing.engine import plan_routes


def test_active_only():
    plan = plan_routes(c.ROUTE_ACTIVE_ONLY, c.PRIORITY_NORMAL, ["d1", "d2"], ["d1", "d2", "d3"])
    assert plan.targets == ["d1"]


def test_active_with_fallback_lists_all_active():
    plan = plan_routes(
        c.ROUTE_ACTIVE_WITH_FALLBACK, c.PRIORITY_NORMAL, ["d1", "d2"], ["d1", "d2", "d3"]
    )
    assert plan.targets == ["d1", "d2"]


def test_low_priority_is_primary_only():
    plan = plan_routes(
        c.ROUTE_ACTIVE_WITH_FALLBACK, c.PRIORITY_LOW, ["d1", "d2"], ["d1", "d2"]
    )
    assert plan.targets == ["d1"]


def test_fallback_to_all_when_no_active():
    plan = plan_routes(c.ROUTE_ACTIVE_WITH_FALLBACK, c.PRIORITY_NORMAL, [], ["d1", "d2"])
    assert plan.targets == ["d1", "d2"]


def test_all_devices_unions_and_dedups():
    plan = plan_routes(c.ROUTE_ALL_DEVICES, c.PRIORITY_CRITICAL, ["d2"], ["d1", "d2", "d3"])
    assert plan.targets == ["d2", "d1", "d3"]


def test_specific_device():
    plan = plan_routes(
        c.ROUTE_SPECIFIC_DEVICE, c.PRIORITY_NORMAL, ["d1"], ["d1", "d2"], specific_device="d2"
    )
    assert plan.targets == ["d2"]


def test_timeout_by_priority():
    assert plan_routes(c.ROUTE_ACTIVE_ONLY, c.PRIORITY_HIGH, ["d1"], ["d1"]).timeout_seconds == 2
    assert plan_routes(c.ROUTE_ACTIVE_ONLY, c.PRIORITY_NORMAL, ["d1"], ["d1"]).timeout_seconds == 5
