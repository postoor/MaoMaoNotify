"""Activity scoring (§16). Pure function, clamped to 0–100."""

from app.presence.schemas import Observation


def compute_activity_score(obs: Observation, *, offline: bool = False) -> int:
    if offline:
        return 0

    score = 0

    li = obs.last_interaction_ms
    if li is not None:
        if li <= 15_000:
            score += 50
        elif li <= 60_000:
            score += 35

    if obs.screen == "on":
        score += 10
    elif obs.screen == "off":
        score -= 30

    if obs.locked is False:
        score += 15
    elif obs.locked is True:
        score -= 40

    if obs.app_state == "foreground":
        score += 20

    if obs.motion == "handheld":
        score += 20
    elif obs.motion == "moving":
        score += 10

    return max(0, min(100, score))


def confidence_from_score(score: int) -> float:
    return round(score / 100, 2)
