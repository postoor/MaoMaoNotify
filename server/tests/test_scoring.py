"""Activity scoring (§16) and the §80 presence scenario."""

from app.presence.schemas import Observation
from app.presence.scoring import compute_activity_score


def test_recent_input_tiers():
    assert compute_activity_score(Observation(last_interaction_ms=10_000)) == 50
    assert compute_activity_score(Observation(last_interaction_ms=30_000)) == 35
    assert compute_activity_score(Observation(last_interaction_ms=120_000)) == 0


def test_screen_and_lock():
    obs = Observation(last_interaction_ms=5_000, screen="on", locked=False)
    assert compute_activity_score(obs) == 75  # 50 + 10 + 15
    obs2 = Observation(screen="off", locked=True)
    assert compute_activity_score(obs2) == 0  # -30 -40 clamped to 0


def test_foreground_and_motion():
    obs = Observation(
        last_interaction_ms=5_000, screen="on", locked=False,
        app_state="foreground", motion="handheld",
    )
    assert compute_activity_score(obs) == 100  # 50+10+15+20+20 = 115 clamp 100


def test_offline_is_zero():
    assert compute_activity_score(Observation(last_interaction_ms=1000), offline=True) == 0


def test_clamped_to_range():
    for li in (0, 15_000, 60_000, 999_999):
        s = compute_activity_score(Observation(last_interaction_ms=li, screen="on", locked=False))
        assert 0 <= s <= 100


def test_scenario_80_mac_beats_idle_phone():
    # Mac: screen on, unlocked, last input 5s
    mac = compute_activity_score(Observation(screen="on", locked=False, last_interaction_ms=5_000))
    # Android: screen on, unlocked, stationary, last input 4 min
    phone = compute_activity_score(
        Observation(screen="on", locked=False, motion="stationary", last_interaction_ms=240_000)
    )
    assert mac > phone
    assert mac == 75 and phone == 25
